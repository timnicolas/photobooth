import client from './client'

export const getPrinterStatus = () => client.get('/printer/status').then((r) => r.data)
export const getPrinterJobs = () => client.get('/printer/jobs').then((r) => r.data)
export const cancelPrinterJob = (id) => client.delete(`/printer/jobs/${id}`).then((r) => r.data)
export const cancelAllPrinterJobs = () => client.delete('/printer/jobs').then((r) => r.data)
