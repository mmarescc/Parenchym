<%inherit file="pym:templates/_layouts/sys.mako" />

<%block name="styles">
${parent.styles()}
<style>
label { width: 6em; display: inline-block; }
</style>
</%block>
<%block name="meta_title">Login</%block>

<div style="width: 500px; margin: 6ex auto;">
    <form action="${url}" method="post">
      <input type="hidden" name="referrer" value="${referrer}"/>
      <input type="hidden" name="XSRF_TOKEN" value="${request.session.get_csrf_token()}"/>
      <label for="login">Login</label> <input id="login" type="text" name="login" value=""/><br/>
      <label for="pwd">Password</label> <input id="pwd" type="password" name="pwd" value=""/><br/>
      <input type="submit" name="submit" value="Log In"/>
    </form>
</div>

<script>
require(['requirejs/domReady!', 'jquery'], function (doc, $) {
	$('#login').focus();
});
</script>

