<%!
import pym.lib
import pym.res
from pprint import pformat
%>
## ===[ BREADCRUMBS ]=======
<%def name="breadcrumbs()">
<%
    bcs=pym.lib.build_breadcrumbs(request)
    bcslen = len(bcs)
%>
    <ul>
% for i, elem in enumerate(bcs):
    % if elem[0]:
        <%
        if elem[0].endswith(('s/', 'mgr/')):
            cls = 'class="manager"'
        else:
            cls = ''
        %>
        <li><a ${cls|n} href="${elem[0]}">${elem[1]}</a></li>
    % else:
        <li><a href="#">${elem[1]}</a></li>
    % endif
    % if i < bcslen - 1:
        <li class="breadcrumb-spacer">&rang;</li>
    % endif
% endfor
    </ul>
</%def>


## ===[ GROWL FLASH ]=======
<%def name="render_flash()">
% for m in pym.lib.build_growl_msgs_nojs(request):
    <div class="ui-widget ui-widget-content ui-corner-all ui-state-${m['type']} flash flash-${m['type']}">
        <div><i class="${m['icon']}"></i>${m['title'] | n}</div>
        <div>${m['text'] | n}</div>
    </div>
% endfor
</%def>

<%def name="growl_flash()">
% for m in pym.lib.build_growl_msgs(request):
    PYM.growl( ${m|n} );
% endfor
</%def>
