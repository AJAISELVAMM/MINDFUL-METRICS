export default function ErrorState({ message = 'Something went wrong.', onRetry }) {
  return (
    <div className="card flex flex-col items-center justify-center px-6 py-12 text-center">
      <p className="text-sm font-semibold text-slate-800">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-3 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white">
          Retry
        </button>
      )}
    </div>
  )
}
