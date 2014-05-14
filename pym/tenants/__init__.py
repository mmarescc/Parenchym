from pyramid.traversal import lineage


def find_tenant(resource):
    """
    Finds the tenant node in the resource tree to which ``resource``
    belongs. The tenant node is the immediate child of root.

    :returns: ``resource``, if ``resource`` is the tenant node, None if
        ``resource`` is root, else the tenant node.
    """
    lin = list(lineage(resource))
    if len(lin) == 1:
        # resource is root, so we cannot find a tenant
        return None
    else:
        # Root is last element (lin[-1]), tenant is 2nd last.
        return lin[-2]
