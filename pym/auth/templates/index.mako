<%inherit file="pym:templates/_layouts/sys.mako" />
<%block name="meta_title">Authentication Manager</%block>
<%block name="styles">
${parent.styles()}
</%block>


<div class="row">
    <div class="col-md-4">
        <ul>
            <li><a href="${request.resource_url(request.context['users'])}">Manage Users</a></li>
            <li><a href="${request.resource_url(request.context['groups'])}">Manage Groups</a></li>
            <li><a href="${request.resource_url(request.context['group_members'])}">Manage Group Members</a></li>
        </ul>
    </div>
</div>

