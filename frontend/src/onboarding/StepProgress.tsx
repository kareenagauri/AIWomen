interface StepProgressProps {
  currentStep: number
  totalSteps: number
  label: string
}

export function StepProgress({ currentStep, totalSteps, label }: StepProgressProps) {
  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <p style={{ color: '#666', marginBottom: '0.5rem' }}>
        Step {currentStep} of {totalSteps} — {label}
      </p>
      <div style={{ display: 'flex', gap: '0.25rem' }}>
        {Array.from({ length: totalSteps }, (_, i) => i + 1).map((step) => (
          <div
            key={step}
            style={{
              flex: 1,
              height: 4,
              borderRadius: 2,
              backgroundColor: step <= currentStep ? '#333' : '#ddd',
            }}
          />
        ))}
      </div>
    </div>
  )
}
