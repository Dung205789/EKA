export function backendBaseUrl() {
  return process.env.EKA_API_URL || 'http://localhost:8000'
}
