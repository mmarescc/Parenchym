<%inherit file="pym:templates/_layouts/default.mako" />
<%block name="meta_title">Choose Your Destination</%block>
<%block name="styles">
${parent.styles()}
</%block>


<div class="outer-gutter">

  %if not tenants:
      <p>Sorry, you do not belong to any tenant.</p>
      <p>Please contact the administrator.</p>
  %else:
      <p>Available Tenants:</p>

      <ul>
        % for t in tenants:
            <li><a href="${request.resource_url(request.context[t.name])}">${t.title}</a></li>
        % endfor
      </ul>
  %endif

</div>
