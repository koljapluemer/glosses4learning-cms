export async function logAi(
  action: string,
  refs: string[],
  payload: Record<string, unknown>
): Promise<void> {
  try {
    await window.electronAPI.aiLog.write({ action, refs, payload })
  } catch (err) {
    console.warn('AI log failed', err)
  }
}
