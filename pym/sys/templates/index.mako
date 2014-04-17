<%!
    from pym.auth.const import NODE_NAME_SYS_AUTH_MGR
%>
<%inherit file="pym:templates/_layouts/sys.mako" />
<%block name="meta_title">System</%block>
<%block name="styles">
${parent.styles()}
</%block>
<%block name="scripts">
${parent.scripts()}
</%block>

<div class="outer-gutter">
<ul>
    <li><a href="${request.resource_url(request.context[NODE_NAME_SYS_AUTH_MGR])}">Authentication Manager</a></li>
</ul>
</div>
