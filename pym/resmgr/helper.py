# ===[ HELP ]=======


def linkto_help(request, *elems, **kw):
    if elems:
        elems = list(elems)
        if '/' in elems[0]:
            a = elems[0].split('/')
            elems = a + list(elems[1:])
        if not elems[0].startswith('@@'):
            elems[0] = '@@' + elems[0]
    return request.resource_url(request.root['help'], *elems, **kw)
