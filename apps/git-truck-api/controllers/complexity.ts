import axios from 'axios'
import { Request, Response } from 'express'
import {
  parseBranchDataforComplexityMetrics,
} from '../utils/htmlParser'

interface TempRepoRequest extends Request {
  repoName?: string
}

const getComplexityMetrics = async (req: TempRepoRequest, res: Response): Promise<void> => {
  const { branch } = req.body
  const { repoName } = req
  
  try {
    const gitTruckUrl = process.env.GIT_TRUCK_URL
    const response = await axios.get(`${gitTruckUrl}/${repoName}/${branch}`)
    const parsedComplexityMetrics = await parseBranchDataforComplexityMetrics(
      response.data
    )
    res.status(200).json(parsedComplexityMetrics)
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(error)
    res.status(500).json({ error: 'Error al obtener métricas de complejidad' })
  }
}

export { getComplexityMetrics }
