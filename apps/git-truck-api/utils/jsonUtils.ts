import { convertUnixTimeToDate, formatDate } from './dateUtils'

interface Author {
  author: string
  contribution: number
}

interface Commit {
  hash: string
  message: string
  date: string
}

interface RawCommit {
  hash: string
  message: string
  time: number
  author: string
}

interface TreeNode {
  type: string
  authors?: Record<string, number>
  children?: TreeNode[]
  lastChangeEpoch?: number
  lastChangeEpochFormatted?: string
  commits?: string[] | Commit[]
  singleAuthor?: boolean
  topContributor?: string
  [key: string]: unknown
}

const updateAuthorValues = (jsonObj: TreeNode): TreeNode => {
  if (Object.prototype.hasOwnProperty.call(jsonObj, 'authors')) {
    const authorKeys = Object.keys(jsonObj.authors!)
    const totalSum = authorKeys.reduce(
      (sum, key) => sum + jsonObj.authors![key],
      0
    )

    const authorsWithPercentage: Author[] = authorKeys.map((key) => {
      const proportion = jsonObj.authors![key] / totalSum
      const percentage = Math.round(proportion * 100)
      return { author: key, contribution: percentage }
    })

    authorsWithPercentage.sort((a, b) => b.contribution - a.contribution)

    const sortedAuthors: Record<string, number> = {}
    authorsWithPercentage.forEach((authorObj) => {
      sortedAuthors[authorObj.author] = authorObj.contribution
    })

    jsonObj.authors = sortedAuthors
  }

  if (Object.prototype.hasOwnProperty.call(jsonObj, 'children')) {
    jsonObj.children!.forEach((child) => {
      updateAuthorValues(child)
    })
  }

  return jsonObj
}

const updateLastChangeDate = (jsonObj: TreeNode): void => {
  if (jsonObj.type === 'blob' && jsonObj.lastChangeEpoch !== undefined) {
    jsonObj.lastChangeEpochFormatted = formatDate(
      convertUnixTimeToDate(jsonObj.lastChangeEpoch)
    )
  } else if (jsonObj.type === 'tree') {
    jsonObj.children!.forEach((child) => {
      updateLastChangeDate(child)
    })
  }
}

const updateCommits = (jsonObj: TreeNode, commitsJson: Record<string, RawCommit>): void => {
  if (jsonObj.type === 'blob' && jsonObj.commits !== undefined) {
    const commitList = jsonObj.commits
      .map((commitHash) => commitsJson[commitHash as string])
      .filter((commit): commit is RawCommit => commit !== undefined)

    commitList.sort((a, b) => b.time - a.time)

    const updatedCommits: Commit[] = commitList.map((commit) => {
      return {
        hash: commit.hash,
        message: commit.message,
        date: formatDate(convertUnixTimeToDate(commit.time)),
      }
    })

    jsonObj.commits = updatedCommits
  } else if (jsonObj.type === 'tree') {
    jsonObj.children!.forEach((child) => {
      updateCommits(child, commitsJson)
    })
  }
}

function updateRepositoryCommits(repositoryJson: TreeNode, commitsJson: Record<string, RawCommit>): void {
  updateCommits(repositoryJson, commitsJson)
}

const addMetrics = (jsonData: TreeNode): void => {
  addSingleAuthor(jsonData)
  addTopContributor(jsonData)
}

const addSingleAuthor = (jsonData: TreeNode): void => {
  if (jsonData.type === 'blob') {
    jsonData.singleAuthor =
      Object.keys(jsonData.authors || {}).length === 1 ? true : false
  }

  if (jsonData.children && jsonData.children.length > 0) {
    for (let i = 0; i < jsonData.children.length; i++) {
      addMetrics(jsonData.children[i])
    }
  }
}

const addTopContributor = (node: TreeNode): void => {
  if (node.type === 'blob') {
    let maxContributions = -1
    let topContributor = ''

    if (node.authors) {
      for (const [author, contribution] of Object.entries(node.authors)) {
        if (contribution > maxContributions) {
          maxContributions = contribution
          topContributor = author
        }
      }
    }

    node.topContributor = topContributor
  }

  if (node.children && node.children.length > 0) {
    for (let i = 0; i < node.children.length; i++) {
      addTopContributor(node.children[i])
    }
  }
}

const getMinCommits = (jsonObj: TreeNode): number => {
  let minCommits = Infinity

  if (jsonObj.type === 'blob' && jsonObj.commits !== undefined) {
    minCommits = Math.min(minCommits, jsonObj.commits.length)
  }

  if (jsonObj.children) {
    jsonObj.children.forEach((child) => {
      minCommits = Math.min(minCommits, getMinCommits(child))
    })
  }

  return minCommits === Infinity ? 0 : minCommits
}

const getMaxCommits = (jsonObj: TreeNode): number => {
  let maxCommits = 0

  if (jsonObj.type === 'blob' && jsonObj.commits !== undefined) {
    maxCommits = Math.max(maxCommits, jsonObj.commits.length)
  }

  if (jsonObj.children) {
    jsonObj.children.forEach((child) => {
      maxCommits = Math.max(maxCommits, getMaxCommits(child))
    })
  }

  return maxCommits
}

const getFirstChangeEpoch = (jsonObj: TreeNode): number => {
  let firstChange = Infinity

  if (jsonObj.type === 'blob' && jsonObj.lastChangeEpoch !== undefined) {
    firstChange = Math.min(firstChange, jsonObj.lastChangeEpoch)
  }

  if (jsonObj.children) {
    jsonObj.children.forEach((child) => {
      firstChange = Math.min(firstChange, getFirstChangeEpoch(child))
    })
  }

  return firstChange === Infinity ? 0 : firstChange
}

const getLastChangeEpoch = (jsonObj: TreeNode): number => {
  let lastChange = 0

  if (jsonObj.type === 'blob' && jsonObj.lastChangeEpoch !== undefined) {
    lastChange = Math.max(lastChange, jsonObj.lastChangeEpoch)
  }

  if (jsonObj.children) {
    jsonObj.children.forEach((child) => {
      lastChange = Math.max(lastChange, getLastChangeEpoch(child))
    })
  }

  return lastChange
}

const simplifyContributions = (jsonObj: TreeNode): TreeNode => {
  const simplifiedObj: TreeNode = { ...jsonObj }

  if (simplifiedObj.authors) {
    const authorKeys = Object.keys(simplifiedObj.authors)
    if (authorKeys.length > 0) {
      const topAuthor = authorKeys[0]
      simplifiedObj.authors = { [topAuthor]: simplifiedObj.authors[topAuthor] }
    }
  }

  if (simplifiedObj.children) {
    simplifiedObj.children = simplifiedObj.children.map((child) =>
      simplifyContributions(child)
    )
  }

  return simplifiedObj
}

const getContributionCommitsDetailed = async (
  commits: RawCommit[],
): Promise<Record<string, RawCommit[]>> => {
  const contributionCommits: Record<string, RawCommit[]> = {}

  if (!commits || !Array.isArray(commits)) {
    return contributionCommits
  }

  for (const commit of commits) {
    const author = commit.author
    if (!contributionCommits[author]) {
      contributionCommits[author] = []
    }
    contributionCommits[author].push(commit)
  }

  return contributionCommits
}

const calculateComplexityMetric = (tree: TreeNode): Record<string, number> => {
  const authorComplexity: Record<string, number> = {}

  const calculateComplexity = (node: TreeNode): number => {
    if (node.type === 'blob') {
      return 1
    }

    if (node.children) {
      return node.children.reduce((sum, child) => sum + calculateComplexity(child), 0)
    }

    return 0
  }

  const traverseTree = (node: TreeNode): void => {
    if (node.authors) {
      for (const [author, ] of Object.entries(node.authors)) {
        if (!authorComplexity[author]) {
          authorComplexity[author] = 0
        }
        authorComplexity[author] += calculateComplexity(node)
      }
    }

    if (node.children) {
      node.children.forEach((child) => traverseTree(child))
    }
  }

  traverseTree(tree)
  return authorComplexity
}

export {
  updateAuthorValues,
  updateLastChangeDate,
  updateCommits,
  updateRepositoryCommits,
  addMetrics,
  addSingleAuthor,
  addTopContributor,
  getMinCommits,
  getMaxCommits,
  getFirstChangeEpoch,
  getLastChangeEpoch,
  simplifyContributions,
  getContributionCommitsDetailed,
  calculateComplexityMetric,
}
