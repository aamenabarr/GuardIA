import { Request, Response, NextFunction } from 'express'
import { promises as fs } from 'fs'

interface TempRepoRequest extends Request {
  tempRepoPath?: string
  gitTruckProcess?: ReturnType<typeof import('child_process').exec>
}

const cleanupMiddleware = async (req: TempRepoRequest, res: Response, next: NextFunction) => {
  let cleaned = false
  
  const originalSend = res.send
  res.send = function(data) {
    if (!cleaned) {
      cleanupTempRepo(req)
      cleaned = true
    }
    return originalSend.call(this, data)
  }

  const originalJson = res.json
  res.json = function(data) {
    if (!cleaned) {
      cleanupTempRepo(req)
      cleaned = true
    }
    return originalJson.call(this, data)
  }

  next()
}

const cleanupTempRepo = async (req: TempRepoRequest) => {
  try {
    if (req.gitTruckProcess) {
      req.gitTruckProcess.kill('SIGTERM')
      
      setTimeout(() => {
        if (req.gitTruckProcess && !req.gitTruckProcess.killed) {
          req.gitTruckProcess.kill('SIGKILL')
        }
      }, 2000)
      
      // eslint-disable-next-line no-console
      console.log('GitTruck detenido')
    }

    if (req.tempRepoPath) {
      await fs.rm(req.tempRepoPath, { recursive: true, force: true })
      // eslint-disable-next-line no-console
      console.log(`Repositorio temporal eliminado: ${req.tempRepoPath}`)
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error limpiando repositorio temporal:', error)
  }
}

export default cleanupMiddleware
