from .const import NOBODY_UID


def group_finder(userid, request):
    """
    Returns list of security principals of the currently logged in user.

    A principal starting with ``u:`` denotes the user, with ``g:`` denotes
    a group. We use the IDs as identifier.

    Nobody has no principals.

    Param 'userid' must match principal of current user, else throws error.
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
    # Insert current user
    gg = ['u:' + str(usr.uid)]
    # That's all if she is not member of any group.
    if not usr.groups:
        return gg
    # Append groups
    gg += ['g:' + str(g[0]) for g in usr.groups]
    return gg