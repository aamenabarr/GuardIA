import {
  updateAuthorValues,
  updateLastChangeDate,
  addMetrics,
  getMinCommits,
  getMaxCommits,
  getFirstChangeEpoch,
  getLastChangeEpoch,
  simplifyContributions,
  getContributionCommitsDetailed,
  calculateComplexityMetric,
} from './jsonUtils'

const parseBranchData = (html: string) => {
  const htmlContent = html
  const scriptContent = htmlContent.match(
    /<script.*?>(window\.__remixContext.*?)<\/script>/s
  )![1]

  const contentWithoutFirstPart = scriptContent.slice(24)
  const contentWithoutLastPart = contentWithoutFirstPart.slice(0, -1)

  const jsonData = JSON.parse(contentWithoutLastPart)
  const repository = jsonData.state.loaderData['routes/$repo.$']
  const authors = repository.analyzerData.authors
  const minCommits = getMinCommits(repository.analyzerData.commit.tree)
  const maxCommits = getMaxCommits(repository.analyzerData.commit.tree)
  const firstChange = getFirstChangeEpoch(repository.analyzerData.commit.tree)
  const lastChange = getLastChangeEpoch(repository.analyzerData.commit.tree)

  const tree = updateAuthorValues(repository.analyzerData.commit.tree)
  updateLastChangeDate(tree)
  addMetrics(tree)

  return { tree, authors, minCommits, maxCommits, firstChange, lastChange }
}

const parseBranchDataforContributions = async (html: string) => {
  const htmlContent = html
  const scriptContent = htmlContent.match(
    /<script.*?>(window\.__remixContext.*?)<\/script>/s
  )![1]

  const contentWithoutFirstPart = scriptContent.slice(24)
  const contentWithoutLastPart = contentWithoutFirstPart.slice(0, -1)

  const jsonData = JSON.parse(contentWithoutLastPart)
  const repository = jsonData.state.loaderData['routes/$repo.$']
  const commits = repository.analyzerData.commits

  const tree = updateAuthorValues(repository.analyzerData.commit.tree)
  const contributionCommits = await getContributionCommitsDetailed(commits)

  const simplifiedTree = simplifyContributions(tree)

  const data = JSON.stringify({ simplifiedTree, contributionCommits }, null, 2)

  return { simplifiedTree, contributionCommits }
}

const parseBranchDataforComplexityMetrics = async (html: string) => {
  const htmlContent = html
  const scriptContent = htmlContent.match(
    /<script.*?>(window\.__remixContext.*?)<\/script>/s
  )![1]

  const contentWithoutFirstPart = scriptContent.slice(24)
  const contentWithoutLastPart = contentWithoutFirstPart.slice(0, -1)

  const jsonData = JSON.parse(contentWithoutLastPart)
  const repository = jsonData.state.loaderData['routes/$repo.$']

  const tree = updateAuthorValues(repository.analyzerData.commit.tree)

  const authorComplexity = calculateComplexityMetric(tree)

  return { authorComplexity }
}

export {
  parseBranchData,
  parseBranchDataforContributions,
  parseBranchDataforComplexityMetrics,
}
