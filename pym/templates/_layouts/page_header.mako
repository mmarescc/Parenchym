<%page args="parent, pym, render_flash" />
<%!
    from pym.resmgr.helper import linkto_help
%>
<%block name="pageHeader" args="parent, pym, render_flash">
    <header>
        % if render_flash:
        <div class="row">
            <div class="col-md-12">${pym.render_flash() | n}</div>
        </div>
        % endif
        <div class="row" id="page_header_top_row">
            <div class="col-md-10" style="display: table-row;">
                <div id="logo" style="display: table-cell; padding-right: 2em;">
                    <a href="${request.resource_url(request.root)}">
                        <img class="img" src="${request.static_url('pym:static/img/pym-logo.png')}" border="0" alt="PYM" />
                    </a>
                </div>
                <div class="page-header" style="display: table-cell;">
                    <h1>${parent.meta_title()}</h1>
                </div>
            </div>
            <div class="col-md-2" id="user_info">
                <div id="user_display_name" style="display: inline-block;">${request.user.display_name}
                    <div id="user_log_in_out" class="hidden-print" style="display: inline-block;">
                        % if request.user.is_auth():
                            <a href="${request.resource_url(request.root, '@@logout')}">Logout</a>
                        % else:
                            <a href="${request.resource_url(request.root, '@@login')}">Login</a>
                        % endif
                    </div>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-md-12" id="breadcrumbs">
                <div class="inner">
                    ${pym.breadcrumbs()}
                </div>
            </div>
        </div>
    </header>
</%block>