import { Request, Response, NextFunction } from 'express'
import { promises as fs } from 'fs'
import path from 'path'
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

interface TempRepoRequest extends Request {
  tempRepoPath?: string
  gitTruckProcess?: ReturnType<typeof import('child_process').exec>
  repoName?: string
}

const tempRepoMiddleware = async (req: TempRepoRequest, res: Response, next: NextFunction) => {
  const { repo } = req.body

  const repoName = path.basename(repo.replace('.git', ''))
  const tempDir = path.join(process.cwd(), 'repo', repoName)

  try {
    await fs.mkdir(path.join(process.cwd(), 'repo'), { recursive: true })
    
    if (await fs.access(tempDir).then(() => true).catch(() => false)) {
      await fs.rm(tempDir, { recursive: true, force: true })
    }

    await execAsync(`git clone ${repo} ${tempDir}`)
    
    // eslint-disable-next-line no-console
    console.log(`Iniciando GitTruck para repositorio: ${repoName}`)
    const gitTruckProcess = exec('npx git-truck@1.4.4 --no-open --headless', {
      cwd: tempDir,
      env: { ...process.env, BROWSER: 'none', OPEN: 'false' }
    })

    await new Promise(resolve => setTimeout(resolve, 5000))

    req.tempRepoPath = tempDir
    req.gitTruckProcess = gitTruckProcess
    req.repoName = repoName

    next()
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('Error en middleware tempRepo:', error)
    res.status(500).json({ error: 'Error al preparar repositorio temporal' })
  }
}

export default tempRepoMiddleware
