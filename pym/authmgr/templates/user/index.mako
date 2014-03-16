<%inherit file="pym:templates/_layouts/sys.mako" />
<%block name="meta_title">Manage Users</%block>
<%block name="styles">
${parent.styles()}
<link rel="stylesheet" href="${request.static_url('pym:static/vendor/angular/ng-grid/ng-grid.css')}">
<style>
.gridStyle {
    border: 1px solid rgb(212,212,212);
    width: 100%;
    height: 300px
}
</style>
</%block>
<%block name="require_config">
	${parent.require_config()}
    // Angular app must inject also these libs
    PYM_APP_REQUIREMENTS.push('ng/ng-grid/ng-grid.min');
    PYM_APP_INJECTS.push('ngGrid');
</%block>

<div ng-controller="MyCtrl">

    <h1>Hello users</h1>

    <div class="gridStyle" ng-grid="gridOptions"></div>



</div>


<script>
require(['requirejs/domReady!', 'ng/angular.min', 'app/app'], function (document, angular, app) {
    'use strict';

    //alert('huhu');
    app.controller('MyCtrl', function($scope) {
        $scope.myData = [
            {name: "Moroni", age: 50},
            {name: "Tiancum", age: 43},
            {name: "Jacob", age: 27},
            {name: "Nephi", age: 29},
            {name: "Enos", age: 34}
        ];
        $scope.gridOptions = { data: 'myData' };
    });


});
</script>