import test from 'node:test'
import assert from 'node:assert/strict'

// Set environment for test
process.env.VITE_API_BASE_URL = 'https://mindful-metrics-api.onrender.com'

// Import modules under test
const {
  buildApiUrl,
  isBackendWarm,
  markBackendHealthy,
  pingBackendHealth,
  ensureBackendReady,
  loginRequest,
} = await import('./src/services/api.js')

test('URL Normalization: buildApiUrl correctly normalizes all path combinations', () => {
  const expectedHealth = 'https://mindful-metrics-api.onrender.com/api/health'
  const expectedLogin = 'https://mindful-metrics-api.onrender.com/api/auth/login'

  assert.equal(buildApiUrl('/health'), expectedHealth)
  assert.equal(buildApiUrl('/api/health'), expectedHealth)
  assert.equal(buildApiUrl('health'), expectedHealth)
  assert.equal(buildApiUrl('/auth/login'), expectedLogin)
  assert.equal(buildApiUrl('/api/auth/login'), expectedLogin)
  assert.equal(buildApiUrl('auth/login'), expectedLogin)
})

test('Health Ping: simulates 502 Bad Gateway and 503 Service Unavailable during cold start', async () => {
  const originalFetch = globalThis.fetch
  try {
    // 1. Simulate 502 Bad Gateway
    globalThis.fetch = async () => new Response('Bad Gateway', { status: 502, statusText: 'Bad Gateway' })
    const res502 = await pingBackendHealth(2000)
    assert.equal(res502.ok, false)
    assert.equal(res502.status, 502)

    // 2. Simulate 503 Service Unavailable
    globalThis.fetch = async () => new Response('Service Unavailable', { status: 503, statusText: 'Service Unavailable' })
    const res503 = await pingBackendHealth(2000)
    assert.equal(res503.ok, false)
    assert.equal(res503.status, 503)

    // 3. Simulate Abort/Timeout
    globalThis.fetch = async () => {
      const err = new Error('The operation was aborted')
      err.name = 'AbortError'
      throw err
    }
    const resTimeout = await pingBackendHealth(2000)
    assert.equal(resTimeout.ok, false)
    assert.equal(resTimeout.error, 'timeout')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('Health Wakeup: Simulates cold-start recovery with retry and backoff', async () => {
  const originalFetch = globalThis.fetch
  let attempts = 0
  const progressMessages = []

  try {
    // Simulate 2 failed probes (e.g. 502/503 during wake-up) followed by 200 OK
    globalThis.fetch = async (url) => {
      attempts++
      if (attempts < 3) {
        return new Response('Waking container...', { status: 503, statusText: 'Service Unavailable' })
      }
      return new Response(JSON.stringify({ ok: true, status: 'ok', product: 'Mindful Metrics' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const res = await ensureBackendReady({
      onProgress: (msg) => progressMessages.push(msg),
      maxAttempts: 5,
      initialDelayMs: 50,
      backoffFactor: 1.2,
      maxDelayMs: 200,
      perAttemptTimeoutMs: 1000,
      totalTimeoutMs: 5000,
      force: true,
    })

    assert.equal(res.ok, true)
    assert.equal(res.attempts, 3)
    assert.equal(attempts, 3)
    assert.ok(progressMessages.length >= 3)
    assert.ok(isBackendWarm(), 'Backend should now be marked warm')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('Health Wakeup: When already warm, skips polling and resolves immediately', async () => {
  const originalFetch = globalThis.fetch
  let fetchCount = 0

  try {
    markBackendHealthy()
    assert.equal(isBackendWarm(), true)

    globalThis.fetch = async () => {
      fetchCount++
      return new Response('{}', { status: 200 })
    }

    const res = await ensureBackendReady({ force: false })
    assert.equal(res.ok, true)
    assert.equal(res.alreadyHealthy, true)
    assert.equal(fetchCount, 0, 'No HTTP request should be made when warm')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('Health Wakeup: Bounded retries and graceful timeout if backend never responds', async () => {
  const originalFetch = globalThis.fetch
  let attempts = 0

  try {
    globalThis.fetch = async () => {
      attempts++
      return new Response('Gateway Timeout', { status: 504 })
    }

    const res = await ensureBackendReady({
      maxAttempts: 3,
      initialDelayMs: 20,
      backoffFactor: 1.0,
      maxDelayMs: 50,
      perAttemptTimeoutMs: 500,
      totalTimeoutMs: 3000,
      force: true,
    })

    assert.equal(res.ok, false)
    assert.equal(res.attempts, 3)
    assert.match(res.error, /longer than expected/i)
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('Login Request: Single submission, correct endpoint & 401 handling without duplicate retries', async () => {
  const originalFetch = globalThis.fetch
  let loginCalls = 0
  let capturedBody = null

  try {
    globalThis.fetch = async (url, options) => {
      if (url.includes('/auth/login')) {
        loginCalls++
        capturedBody = JSON.parse(options.body)
        return new Response(JSON.stringify({ detail: 'Invalid credentials' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response('Not found', { status: 404 })
    }

    await assert.rejects(
      async () => {
        await loginRequest('employee@mindfulmetrics.com', 'wrongpassword')
      },
      (err) => {
        assert.equal(err.message, 'Invalid credentials')
        assert.equal(err.status, 401)
        // Ensure error message does not expose password
        assert.ok(!err.message.includes('wrongpassword'))
        return true
      }
    )

    // Verify it was called exactly once
    assert.equal(loginCalls, 1)
    assert.equal(capturedBody.email, 'employee@mindfulmetrics.com')
    assert.equal(capturedBody.password, 'wrongpassword')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('Duplicate Submission Guard: Prevents concurrent multiple login requests', async () => {
  let isSubmitting = false
  let submissionCount = 0

  async function mockSubmitFlow() {
    if (isSubmitting) return 'duplicate_blocked'
    isSubmitting = true
    submissionCount++
    await new Promise((r) => setTimeout(r, 100))
    isSubmitting = false
    return 'submitted'
  }

  // Trigger 3 concurrent submissions simultaneously
  const results = await Promise.all([
    mockSubmitFlow(),
    mockSubmitFlow(),
    mockSubmitFlow(),
  ])

  assert.equal(submissionCount, 1, 'Only one submission should proceed')
  assert.equal(results[0], 'submitted')
  assert.equal(results[1], 'duplicate_blocked')
  assert.equal(results[2], 'duplicate_blocked')
})

test('In-Flight Deduplication: Multiple concurrent pingBackendHealth calls share single fetch', async () => {
  const originalFetch = globalThis.fetch
  let fetchCount = 0

  try {
    globalThis.fetch = async () => {
      fetchCount++
      await new Promise((r) => setTimeout(r, 50))
      return new Response(JSON.stringify({ ok: true, status: 'ok' }), { status: 200 })
    }

    // Launch 3 simultaneous health pings
    const [r1, r2, r3] = await Promise.all([
      pingBackendHealth(2000),
      pingBackendHealth(2000),
      pingBackendHealth(2000),
    ])

    assert.equal(fetchCount, 1, 'Only one HTTP request should be sent for concurrent health pings')
    assert.equal(r1.ok, true)
    assert.equal(r2.ok, true)
    assert.equal(r3.ok, true)
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('In-Flight Deduplication: ensureBackendReady attaches to active wake loop without duplicate loop', async () => {
  const originalFetch = globalThis.fetch
  let fetchCount = 0

  try {
    globalThis.fetch = async () => {
      fetchCount++
      if (fetchCount === 1) {
        return new Response('Waking...', { status: 503 })
      }
      return new Response(JSON.stringify({ ok: true, status: 'ok' }), { status: 200 })
    }

    // Start background wake loop
    const wakePromise = ensureBackendReady({
      force: true,
      initialDelayMs: 40,
      backoffFactor: 1.2,
      maxDelayMs: 100,
      totalTimeoutMs: 3000,
    })

    // Simulate user submitting login while wake loop is already in-flight
    const attachPromise = ensureBackendReady()

    const [wakeRes, attachRes] = await Promise.all([wakePromise, attachPromise])

    assert.equal(wakeRes.ok, true)
    assert.equal(attachRes.ok, true)
    assert.equal(fetchCount, 2, 'Both promises should share the same retry loop')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('Live Backend: Health check against deployed Render service', async () => {
  const liveHealthUrl = 'https://mindful-metrics-api.onrender.com/api/health'
  console.log(`Connecting to live Render backend: ${liveHealthUrl}...`)

  const res = await fetch(liveHealthUrl, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
    signal: AbortSignal.timeout(20000),
  })

  assert.equal(res.status, 200, 'Render health endpoint should return 200 OK')
  const data = await res.json()
  assert.equal(data.ok, true, 'Render health endpoint response should have ok: true')
  assert.equal(data.product, 'Mindful Metrics', 'Product title should match')
  console.log('Live Render backend response:', data)
})

test('Live Backend: Login endpoint contract verification with invalid credentials', async () => {
  const liveLoginUrl = 'https://mindful-metrics-api.onrender.com/api/auth/login'
  console.log(`Verifying live Render login endpoint contract: ${liveLoginUrl}...`)

  const res = await fetch(liveLoginUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: 'nonexistent-probe@mindfulmetrics.com',
      password: 'invalid-password-test',
    }),
    signal: AbortSignal.timeout(20000),
  })

  assert.equal(res.status, 401, 'Live backend should reject invalid credentials with 401 Unauthorized')
  const body = await res.json()
  assert.equal(body.detail, 'Invalid credentials', 'Detail message should match')
  console.log('Live Render login 401 contract verified:', body)
})
