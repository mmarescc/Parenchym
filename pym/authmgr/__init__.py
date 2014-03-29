from .const import NOBODY_UID


def group_finder(userid, request):
    """
    Returns role_names of the currently logged in user.

    Role names are prefixed with 'r:'.
    Nobody has no role_names.
    Param 'userid' must match principal of current user, else throws error
    """
    usr = request.user
    # unauthenticated_userid becomes authenticated_userid if groupfinder
    # returns not None.
    if userid != usr.principal:
        # This should not happen (tm)
        raise Exception("Userid '{0}' does not match current "
            "user.principal '{1}'".format(
                userid, usr.principal))
    # Not authenticated users have no groups
    if usr.uid == NOBODY_UID:
        return []
    if not usr.group_names:
        return []
    group_names = ['g:' + g for g in usr.group_names]
    return group_names