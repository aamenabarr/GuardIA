import axios from 'axios'
import { Request, Response } from 'express'
import { parseBranchDataforContributions } from '../utils/htmlParser'

interface TempRepoRequest extends Request {
  repoName?: string
}

const getContributionsData = async (req: TempRepoRequest, res: Response): Promise<void> => {
  const { branch } = req.body
  const { repoName } = req
  
  try {
    const gitTruckUrl = process.env.GIT_TRUCK_URL
    const response = await axios.get(`${gitTruckUrl}/${repoName}/${branch}`)
    const parsedContributions = await parseBranchDataforContributions(
      response.data
    )
    res.status(200).json(parsedContributions)
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(error)
    res.status(500).json({ error: 'Error al obtener datos de contribuciones' })
  }
}

export { getContributionsData }
