const KEY = 'ocr_files'

function getFiles() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveFiles(files) {
  localStorage.setItem(KEY, JSON.stringify(files))
}

export function listFiles() {
  return getFiles()
}

export function addFile({ name, size, src, pages = 0 }) {
  const files = getFiles()
  const id = (crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now() + Math.random())
  const item = {
    id,
    name,
    size,
    src,
    pages,
    ocrProgress: 0,
    proofProgress: 0,
    uploadedAt: Date.now()
  }
  files.push(item)
  saveFiles(files)
  return id
}

export function getFile(id) {
  return getFiles().find(f => f.id === id)
}

export function updateFile(id, partial) {
  const files = getFiles()
  const i = files.findIndex(f => f.id === id)
  if (i >= 0) {
    files[i] = { ...files[i], ...partial }
    saveFiles(files)
  }
}

export function removeFile(id) {
  const files = getFiles().filter(f => f.id !== id)
  saveFiles(files)
}

