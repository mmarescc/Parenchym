<%inherit file="pym:templates/_layouts/sys.mako" />
<%block name="meta_title">Authentication Manager</%block>
<%block name="styles">
${parent.styles()}
</%block>

<div class="outer-gutter">

<ul>
    <li><a href="${request.resource_url(request.context['user'])}">Manage Users</a></li>
    <li><a href="${request.resource_url(request.context['group'])}">Manage Groups</a></li>
    <li><a href="${request.resource_url(request.context['group_member'])}">Manage Group Members</a></li>
</ul>

</div>