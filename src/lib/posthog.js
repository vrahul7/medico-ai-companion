import posthog from 'posthog-js'

export const initPostHog = () => {
  posthog.init(import.meta.env.VITE_POSTHOG_KEY || 'mock-ph-key', {
    api_host: import.meta.env.VITE_POSTHOG_HOST || 'https://app.posthog.com',
    autocapture: false, // Disabling autocapture to save on commercial telemetry costs and ensure zero HIPAA leakage via random clicks
  })
}
