import { useState, useEffect, useRef } from 'react'
import {
  Camera,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  Lock,
  User as UserIcon,
  Mail,
  Phone,
  Building2,
  BadgeCheck,
  Pencil,
  X,
  ShieldCheck,
  Loader2,
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import {
  getUserProfile,
  updateUserProfile,
  uploadAvatar,
  removeAvatar,
  changePassword,
} from '../../services/api'
import LoadingSkeleton from '../../components/common/LoadingSkeleton'

export default function Settings() {
  const { user, updateSession } = useAuth()
  const [profile, setProfile] = useState(user || {})
  const [loading, setLoading] = useState(true)

  // Edit Profile state
  const [isEditing, setIsEditing] = useState(false)
  const [form, setForm] = useState({
    name: '',
    phone: '',
    department: '',
  })
  const [savingProfile, setSavingProfile] = useState(false)
  const [profileMsg, setProfileMsg] = useState('')
  const [profileErr, setProfileErr] = useState('')

  // Avatar upload state
  const fileInputRef = useRef(null)
  const [avatarLoading, setAvatarLoading] = useState(false)
  const [avatarMsg, setAvatarMsg] = useState('')
  const [avatarErr, setAvatarErr] = useState('')

  // Change Password state
  const [passwords, setPasswords] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  })
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [changingPass, setChangingPass] = useState(false)
  const [passMsg, setPassMsg] = useState('')
  const [passErr, setPassErr] = useState('')

  useEffect(() => {
    loadProfile()
  }, [])

  async function loadProfile() {
    setLoading(true)
    try {
      const data = await getUserProfile()
      setProfile(data)
      setForm({
        name: data.name || '',
        phone: data.phone || '',
        department: data.department || '',
      })
    } catch {
      if (user) {
        setProfile(user)
        setForm({
          name: user.name || '',
          phone: user.phone || '',
          department: user.department || '',
        })
      }
    } finally {
      setLoading(false)
    }
  }

  // -------------------------------------------------------------
  // Profile Picture Handlers
  // -------------------------------------------------------------
  function handlePhotoSelect(e) {
    const file = e.target.files?.[0]
    if (!file) return

    setAvatarErr('')
    setAvatarMsg('')

    // Validate format
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    if (!validTypes.includes(file.type.toLowerCase())) {
      setAvatarErr('Please upload a valid image file (JPG, JPEG, PNG, or WebP).')
      return
    }

    // Validate size (max 2.5 MB)
    if (file.size > 2.5 * 1024 * 1024) {
      setAvatarErr('File size must be under 2.5 MB.')
      return
    }

    const reader = new FileReader()
    reader.onload = async () => {
      const base64Data = reader.result
      setAvatarLoading(true)
      try {
        const res = await uploadAvatar(base64Data)
        if (res.ok) {
          setProfile((prev) => ({ ...prev, avatar: base64Data }))
          updateSession({ avatar: base64Data })
          setAvatarMsg('Profile photo updated successfully.')
          setTimeout(() => setAvatarMsg(''), 4000)
        } else {
          setAvatarErr(res.error || 'Failed to upload photo.')
        }
      } catch (err) {
        setAvatarErr(err.message || 'Failed to upload photo.')
      } finally {
        setAvatarLoading(false)
        if (fileInputRef.current) fileInputRef.current.value = ''
      }
    }
    reader.onerror = () => {
      setAvatarErr('Failed to read image file.')
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
    reader.readAsDataURL(file)
  }

  async function handleRemovePhoto() {
    if (!profile.avatar) return
    setAvatarLoading(true)
    setAvatarErr('')
    setAvatarMsg('')
    try {
      const res = await removeAvatar()
      if (res.ok) {
        setProfile((prev) => ({ ...prev, avatar: null }))
        updateSession({ avatar: null })
        setAvatarMsg('Profile photo removed.')
        setTimeout(() => setAvatarMsg(''), 4000)
      } else {
        setAvatarErr(res.error || 'Failed to remove photo.')
      }
    } catch (err) {
      setAvatarErr(err.message || 'Failed to remove photo.')
    } finally {
      setAvatarLoading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  // -------------------------------------------------------------
  // Personal Info Edit Handlers
  // -------------------------------------------------------------
  function handleStartEditing() {
    setProfileErr('')
    setProfileMsg('')
    setForm({
      name: profile.name || '',
      phone: profile.phone || '',
      department: profile.department || '',
    })
    setIsEditing(true)
  }

  function handleCancelEditing() {
    setIsEditing(false)
    setProfileErr('')
    setForm({
      name: profile.name || '',
      phone: profile.phone || '',
      department: profile.department || '',
    })
  }

  async function handleSaveProfile(e) {
    e.preventDefault()
    setProfileErr('')
    setProfileMsg('')

    const trimmedName = form.name.trim()
    if (!trimmedName || trimmedName.length < 2) {
      setProfileErr('Full name must be at least 2 characters.')
      return
    }

    const trimmedPhone = form.phone.trim()
    if (trimmedPhone && trimmedPhone.length < 6) {
      setProfileErr('Please provide a valid phone number (minimum 6 digits).')
      return
    }

    setSavingProfile(true)
    try {
      const payload = {
        name: trimmedName,
        phone: trimmedPhone || '+91 98765 43210',
        department: form.department.trim() || profile.department,
      }
      const res = await updateUserProfile(payload)
      if (res.ok && res.user) {
        setProfile(res.user)
        updateSession({
          name: res.user.name,
          phone: res.user.phone,
          department: res.user.department,
        })
        setProfileMsg('Personal information updated successfully.')
        setIsEditing(false)
        setTimeout(() => setProfileMsg(''), 4000)
      } else {
        setProfileErr(res.error || 'Failed to update personal information.')
      }
    } catch (err) {
      setProfileErr(err.message || 'Failed to update personal information.')
    } finally {
      setSavingProfile(false)
    }
  }

  // -------------------------------------------------------------
  // Change Password Handlers
  // -------------------------------------------------------------
  async function handleChangePassword(e) {
    e.preventDefault()
    setPassErr('')
    setPassMsg('')

    const { currentPassword, newPassword, confirmPassword } = passwords

    if (!currentPassword) {
      setPassErr('Please enter your current password.')
      return
    }
    if (!newPassword) {
      setPassErr('Please enter a new password.')
      return
    }
    if (newPassword.length < 6) {
      setPassErr('New password must be at least 6 characters long.')
      return
    }
    if (newPassword !== confirmPassword) {
      setPassErr('New password and confirmation do not match.')
      return
    }
    if (newPassword === currentPassword) {
      setPassErr('New password cannot be the same as your current password.')
      return
    }

    setChangingPass(true)
    try {
      const res = await changePassword(currentPassword, newPassword)
      if (res.ok) {
        setPassMsg('Password changed successfully.')
        setPasswords({
          currentPassword: '',
          newPassword: '',
          confirmPassword: '',
        })
        setTimeout(() => setPassMsg(''), 4000)
      } else {
        setPassErr(res.error || 'Failed to change password.')
      }
    } catch (err) {
      setPassErr(err.message || 'Current password is incorrect.')
    } finally {
      setChangingPass(false)
    }
  }

  if (loading) return <LoadingSkeleton rows={3} />

  const displayName = profile.name || user?.name || 'User'
  const initials = displayName
    .split(' ')
    .filter(Boolean)
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  const roleFormatted = (profile.role || user?.role || 'employee').toUpperCase()

  return (
    <div className="page-stack fade-in max-w-4xl space-y-6">
      {/* ============================================================ */}
      {/* 1. PERSONAL INFORMATION SECTION */}
      {/* ============================================================ */}
      <section className="card p-6 bg-white border border-[#E2EAF2] rounded-2xl shadow-sm transition-all">
        {/* Section Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E2EAF2] pb-4">
          <div>
            <h2 className="text-[17px] font-bold text-[#0D192B] tracking-tight">
              Personal Information
            </h2>
            <p className="text-[12px] text-[#64748B] mt-0.5">
              View and manage your personal details and workplace identity.
            </p>
          </div>

          {!isEditing && (
            <button
              type="button"
              onClick={handleStartEditing}
              className="inline-flex items-center gap-1.5 btn-secondary text-[12px] px-3.5 py-1.5 rounded-xl font-semibold shadow-xs"
            >
              <Pencil size={14} className="text-[#1E6BFF]" />
              <span>Edit Profile</span>
            </button>
          )}
        </div>

        {/* Global Feedback Banners for Personal Info */}
        {profileMsg && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-[12px] font-medium text-emerald-700 fade-in">
            <CheckCircle2 size={16} className="shrink-0 text-emerald-600" />
            <span>{profileMsg}</span>
          </div>
        )}
        {profileErr && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-[12px] font-medium text-rose-700 fade-in">
            <AlertCircle size={16} className="shrink-0 text-rose-600" />
            <span>{profileErr}</span>
          </div>
        )}

        {/* Profile Picture Controls */}
        <div className="mt-6 flex flex-wrap items-center gap-5 pb-6 border-b border-[#E2EAF2]">
          {/* Avatar Preview */}
          <div className="relative group">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-[#0B1727] text-xl font-bold text-white shadow-sm ring-4 ring-[#EFF6FF] overflow-hidden">
              {profile.avatar ? (
                <img
                  src={profile.avatar}
                  alt={displayName}
                  className="h-full w-full object-cover"
                />
              ) : (
                <span>{initials || 'MM'}</span>
              )}
            </div>

            {avatarLoading && (
              <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/40 text-white">
                <Loader2 size={20} className="animate-spin" />
              </div>
            )}
          </div>

          {/* Action Buttons & Guidance */}
          <div className="flex-1 min-w-[200px]">
            <input
              type="file"
              ref={fileInputRef}
              accept="image/png,image/jpeg,image/jpg,image/webp"
              onChange={handlePhotoSelect}
              className="hidden"
            />

            <div className="flex flex-wrap items-center gap-2.5">
              <button
                type="button"
                disabled={avatarLoading}
                onClick={() => fileInputRef.current?.click()}
                className="btn-primary text-[12px] py-2 px-4 rounded-xl shadow-xs inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <Camera size={14} />
                <span>{profile.avatar ? 'Change Photo' : 'Upload Photo'}</span>
              </button>

              {profile.avatar && (
                <button
                  type="button"
                  disabled={avatarLoading}
                  onClick={handleRemovePhoto}
                  className="btn-secondary text-[12px] py-2 px-3.5 rounded-xl border-rose-200 text-rose-600 hover:bg-rose-50 inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  <Trash2 size={14} />
                  <span>Remove Photo</span>
                </button>
              )}
            </div>

            <p className="mt-1.5 text-[11px] text-[#94A3B8]">
              Allowed JPG, JPEG, PNG, or WebP. Max 2.5 MB.
            </p>

            {avatarMsg && (
              <p className="mt-1 text-[11px] font-medium text-emerald-600 flex items-center gap-1">
                <CheckCircle2 size={12} /> {avatarMsg}
              </p>
            )}
            {avatarErr && (
              <p className="mt-1 text-[11px] font-medium text-rose-600 flex items-center gap-1">
                <AlertCircle size={12} /> {avatarErr}
              </p>
            )}
          </div>
        </div>

        {/* Profile Information View / Edit Form */}
        {!isEditing ? (
          /* READ-ONLY DISPLAY */
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5 text-[13px]">
            {/* Full Name */}
            <div className="rounded-xl border border-[#E2EAF2] bg-[#F8FAFC]/50 p-3.5">
              <span className="text-[11px] font-semibold text-[#64748B] flex items-center gap-1.5">
                <UserIcon size={13} className="text-[#1E6BFF]" />
                Full Name
              </span>
              <p className="mt-1 text-[13px] font-bold text-[#0D192B]">
                {profile.name || '—'}
              </p>
            </div>

            {/* Employee ID / Roll Number */}
            <div className="rounded-xl border border-[#E2EAF2] bg-[#F8FAFC]/50 p-3.5">
              <span className="text-[11px] font-semibold text-[#64748B] flex items-center gap-1.5">
                <BadgeCheck size={13} className="text-[#1E6BFF]" />
                Employee ID / Roll Number
              </span>
              <p className="mt-1 text-[13px] font-bold text-[#0D192B]">
                {profile.employeeId || 'E118'}
              </p>
            </div>

            {/* Department */}
            <div className="rounded-xl border border-[#E2EAF2] bg-[#F8FAFC]/50 p-3.5">
              <span className="text-[11px] font-semibold text-[#64748B] flex items-center gap-1.5">
                <Building2 size={13} className="text-[#1E6BFF]" />
                Department
              </span>
              <p className="mt-1 text-[13px] font-bold text-[#0D192B]">
                {profile.department || 'Engineering'}
              </p>
            </div>

            {/* Role */}
            <div className="rounded-xl border border-[#E2EAF2] bg-[#F8FAFC]/50 p-3.5">
              <span className="text-[11px] font-semibold text-[#64748B] flex items-center gap-1.5">
                <ShieldCheck size={13} className="text-[#1E6BFF]" />
                Role
              </span>
              <div className="mt-1">
                <span className="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-2.5 py-0.5 text-[11px] font-bold text-[#1E6BFF]">
                  {roleFormatted}
                </span>
              </div>
            </div>

            {/* Email */}
            <div className="rounded-xl border border-[#E2EAF2] bg-[#F8FAFC]/50 p-3.5">
              <span className="text-[11px] font-semibold text-[#64748B] flex items-center gap-1.5">
                <Mail size={13} className="text-[#1E6BFF]" />
                Email
              </span>
              <p className="mt-1 text-[13px] font-bold text-[#0D192B] truncate">
                {profile.email || '—'}
              </p>
            </div>

            {/* Phone Number */}
            <div className="rounded-xl border border-[#E2EAF2] bg-[#F8FAFC]/50 p-3.5">
              <span className="text-[11px] font-semibold text-[#64748B] flex items-center gap-1.5">
                <Phone size={13} className="text-[#1E6BFF]" />
                Phone Number
              </span>
              <p className="mt-1 text-[13px] font-bold text-[#0D192B]">
                {profile.phone || '+91 98765 43210'}
              </p>
            </div>
          </div>
        ) : (
          /* EDITABLE FORM */
          <form onSubmit={handleSaveProfile} className="mt-6 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {/* Full Name (Editable) */}
              <div>
                <label className="block text-[11px] font-semibold text-[#0D192B] mb-1">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Enter your full name"
                  className="ww-input"
                  required
                />
              </div>

              {/* Phone Number (Editable) */}
              <div>
                <label className="block text-[11px] font-semibold text-[#0D192B] mb-1">
                  Phone Number
                </label>
                <input
                  type="tel"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  placeholder="+91 98765 43210"
                  className="ww-input"
                />
              </div>

              {/* Department (Editable) */}
              <div>
                <label className="block text-[11px] font-semibold text-[#0D192B] mb-1">
                  Department
                </label>
                <input
                  type="text"
                  value={form.department}
                  onChange={(e) => setForm({ ...form, department: e.target.value })}
                  placeholder="Engineering"
                  className="ww-input"
                />
              </div>

              {/* Employee ID (Read-only) */}
              <div>
                <label className="block text-[11px] font-semibold text-[#64748B] mb-1">
                  Employee ID (Read-only)
                </label>
                <input
                  type="text"
                  value={profile.employeeId || 'E118'}
                  disabled
                  className="ww-input bg-slate-100 text-[#64748B] cursor-not-allowed"
                />
              </div>

              {/* Email (Read-only) */}
              <div>
                <label className="block text-[11px] font-semibold text-[#64748B] mb-1">
                  Email (Managed by Org)
                </label>
                <input
                  type="email"
                  value={profile.email || ''}
                  disabled
                  className="ww-input bg-slate-100 text-[#64748B] cursor-not-allowed"
                />
              </div>

              {/* Role (Read-only) */}
              <div>
                <label className="block text-[11px] font-semibold text-[#64748B] mb-1">
                  Role (Assigned)
                </label>
                <input
                  type="text"
                  value={roleFormatted}
                  disabled
                  className="ww-input bg-slate-100 text-[#64748B] cursor-not-allowed uppercase"
                />
              </div>
            </div>

            {/* Edit Action Buttons */}
            <div className="flex items-center gap-3 pt-3">
              <button
                type="submit"
                disabled={savingProfile}
                className="btn-primary text-[13px] py-2 px-5 rounded-xl font-semibold inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                {savingProfile ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    <span>Saving Changes...</span>
                  </>
                ) : (
                  <span>Save Changes</span>
                )}
              </button>

              <button
                type="button"
                disabled={savingProfile}
                onClick={handleCancelEditing}
                className="btn-secondary text-[13px] py-2 px-4 rounded-xl font-semibold inline-flex items-center gap-1.5 cursor-pointer"
              >
                <X size={14} />
                <span>Cancel</span>
              </button>
            </div>
          </form>
        )}
      </section>

      {/* ============================================================ */}
      {/* 2. CHANGE PASSWORD SECTION */}
      {/* ============================================================ */}
      <section className="card p-6 bg-white border border-[#E2EAF2] rounded-2xl shadow-sm transition-all">
        {/* Section Header */}
        <div className="border-b border-[#E2EAF2] pb-4">
          <h2 className="text-[17px] font-bold text-[#0D192B] tracking-tight">
            Change Password
          </h2>
          <p className="text-[12px] text-[#64748B] mt-0.5">
            Keep your account secure with a strong password of at least 6 characters.
          </p>
        </div>

        {/* Success / Error Banners */}
        {passMsg && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-[12px] font-medium text-emerald-700 fade-in">
            <CheckCircle2 size={16} className="shrink-0 text-emerald-600" />
            <span>{passMsg}</span>
          </div>
        )}
        {passErr && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-[12px] font-medium text-rose-700 fade-in">
            <AlertCircle size={16} className="shrink-0 text-rose-600" />
            <span>{passErr}</span>
          </div>
        )}

        <form onSubmit={handleChangePassword} className="mt-6 max-w-lg space-y-4">
          {/* Current Password Field */}
          <div>
            <label className="block text-[12px] font-semibold text-[#0D192B] mb-1.5">
              Current Password <span className="text-rose-500">*</span>
            </label>
            <div className="relative flex items-center">
              <input
                type={showCurrent ? 'text' : 'password'}
                value={passwords.currentPassword}
                onChange={(e) =>
                  setPasswords({ ...passwords, currentPassword: e.target.value })
                }
                placeholder="Enter current password"
                className="ww-input pr-10"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowCurrent(!showCurrent)}
                className="absolute right-3 text-[#94A3B8] hover:text-[#0D192B] transition cursor-pointer"
                aria-label="Toggle current password visibility"
              >
                {showCurrent ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* New Password Field */}
          <div>
            <label className="block text-[12px] font-semibold text-[#0D192B] mb-1.5">
              New Password <span className="text-rose-500">*</span>
            </label>
            <div className="relative flex items-center">
              <input
                type={showNew ? 'text' : 'password'}
                value={passwords.newPassword}
                onChange={(e) =>
                  setPasswords({ ...passwords, newPassword: e.target.value })
                }
                placeholder="Enter new password (min. 6 characters)"
                className="ww-input pr-10"
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowNew(!showNew)}
                className="absolute right-3 text-[#94A3B8] hover:text-[#0D192B] transition cursor-pointer"
                aria-label="Toggle new password visibility"
              >
                {showNew ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Confirm New Password Field */}
          <div>
            <label className="block text-[12px] font-semibold text-[#0D192B] mb-1.5">
              Confirm New Password <span className="text-rose-500">*</span>
            </label>
            <div className="relative flex items-center">
              <input
                type={showConfirm ? 'text' : 'password'}
                value={passwords.confirmPassword}
                onChange={(e) =>
                  setPasswords({ ...passwords, confirmPassword: e.target.value })
                }
                placeholder="Re-enter new password"
                className="ww-input pr-10"
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirm(!showConfirm)}
                className="absolute right-3 text-[#94A3B8] hover:text-[#0D192B] transition cursor-pointer"
                aria-label="Toggle confirm password visibility"
              >
                {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* Submit Action */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={changingPass}
              className="btn-primary text-[13px] py-2.5 px-6 rounded-xl font-semibold inline-flex items-center gap-2 shadow-sm cursor-pointer disabled:opacity-50"
            >
              {changingPass ? (
                <>
                  <Loader2 size={15} className="animate-spin" />
                  <span>Updating Password...</span>
                </>
              ) : (
                <>
                  <Lock size={15} />
                  <span>Change Password</span>
                </>
              )}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
