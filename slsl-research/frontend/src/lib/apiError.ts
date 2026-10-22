export async function readApiError(res: Response): Promise<string> {
  const text = await res.text()
  if (!text) return `Request failed (${res.status})`
  try {
    const data = JSON.parse(text) as { detail?: string | Array<{ msg?: string; loc?: string[] }> }
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) {
      return data.detail.map((item) => item.msg ?? JSON.stringify(item)).join('; ')
    }
    return text
  } catch {
    return text
  }
}
