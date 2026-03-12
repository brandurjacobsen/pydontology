module.exports = async ({
  github,
  context,
  core,
  username,
  requiredPermission = "write",
}) => {
  try {
    const response = await github.rest.repos.getCollaboratorPermissionLevel({
      owner: context.repo.owner,
      repo: context.repo.repo,
      username: username,
    });

    const permission = response.data.permission;

    const permissionLevels = {
      read: 1,
      triage: 2,
      write: 3,
      maintain: 4,
      admin: 5,
    };

    const hasPermission =
      permissionLevels[permission] >= permissionLevels[requiredPermission];

    core.setOutput("authorized", hasPermission);

    if (!hasPermission) {
      core.setFailed(
        `User ${username} has ${permission} permission, but ${requiredPermission} is required`,
      );
    }

    return hasPermission;
  } catch (error) {
    core.setOutput("authorized", false);
    core.setFailed(`User ${username} is not a collaborator: ${error.message}`);
    return false;
  }
};
