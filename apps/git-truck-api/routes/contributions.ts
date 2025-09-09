import express from 'express'
import { getContributionsData } from '../controllers/contribution'

const router = express.Router()

router.get('/', getContributionsData)

export default router
