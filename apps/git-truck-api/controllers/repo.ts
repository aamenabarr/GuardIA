import axios from 'axios'
import { Request, Response } from 'express'
import { parseBranchData } from '../utils/htmlParser'

interface TempRepoRequest extends Request {
  repoName?: string
}

const getRepoData = async (req: TempRepoRequest, res: Response): Promise<void> => {
  const { branch } = req.body
  const { repoName } = req
  
  try {
    const gitTruckUrl = process.env.GIT_TRUCK_URL
    const response = await axios.get(`${gitTruckUrl}/${repoName}/${branch}`)
    const parsedBranchData = parseBranchData(response.data)
    res.status(200).json(parsedBranchData)
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(error)
    res.status(500).json({ error: 'Error al obtener datos del repositorio' })
  }
}

export { getRepoData }
