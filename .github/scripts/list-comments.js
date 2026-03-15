module.exports = async ({ github, context, core }) => {
  try {
    const comments = await github.rest.issues.listComments({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: context.issue.number
    });
    
    return comments.data.map(c => {
      const isOwner = c.user.login === context.repo.owner;
      const prefix = isOwner ? '👑 **OWNER**' : '**';
      return `${prefix}${c.user.login}** (${c.created_at}):\n${c.body}`;
    }).join('\n\n---\n\n');
  } catch (error) {
    core.setFailed(`Failed to fetch comments: ${error.message}`);
    return '';
  }
};
