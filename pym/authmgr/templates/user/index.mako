<%inherit file="pym:templates/_layouts/sys.mako" />
<%block name="meta_title">Manage Users</%block>
<%block name="styles">
${parent.styles()}
<link rel="stylesheet" href="${request.static_url('pym:static/vendor/angular/ng-grid/ng-grid.css')}">
<link rel="stylesheet" href="${request.static_url('pym:static/vendor/jquery/ui/themes/humanity/jquery.ui.theme.css')}">

<style>
.crud-grid {
    border: 1px solid rgb(212,212,212);
    height: 300px;
  /*  font-size: 90%;*/
}
</style>
</%block>
<%block name="require_config">
	${parent.require_config()}
    // Angular app must inject also these libs
    PYM_APP_REQUIREMENTS.push(
        'app/__sys__/authmgr/users'
    );
    PYM_APP_INJECTS.push('sys_authmgr_users');
</%block>

<script type="text/ng-template" id="browse.html">
    <div class="crud-grid" ng-grid="crud_grid.options"></div>
    <div class="selectedItems">{{crud_grid.selected}}</div>
    <div class="btn-group">
        <button ng-click="goto_view()" type="button" class="btn btn-default btn-xs"><i class="fa fa-file-text-o"></i></button>
        <button type="button" class="btn btn-default btn-xs"><i class="fa fa-plus"></i></button>
        <button type="button" class="btn btn-default btn-xs"><i class="fa fa-pencil"></i></button>
        <button type="button" class="btn btn-default btn-xs"><i class="fa fa-trash-o"></i></button>
        <button type="button" class="btn btn-default btn-xs"><i class="fa fa-refresh"></i></button>
        <button type="button" class="btn btn-default btn-xs"><i class="fa fa-save"></i></button>
    </div>
</script>
<script type="text/ng-template" id="view.html">
    <p>Details of {{entity.display_name}}</p>
    <div class="btn-group">
        <button ng-click="state.go('browse')" type="button" class="btn btn-default"><i class="fa fa-arrow-left"> Close</i></button>
    </div>
</script>


<div class="content-margin-top" ng-controller="ContentCtrl">
    <div ui-view></div>
</div>

<script>
require(['requirejs/domReady!', 'ng/angular.min', 'app/app', 'ng/ng-grid/ng-grid.min'], function (document, angular, PymApp) {
    'use strict';

    PymApp.constant('URLS', ${urls|n});


    var checkbox_cell_template = '<div class="ngSelectionCell"><input tabindex="-1" class="ngSelectionCheckbox" type="checkbox" ng-checked="row.getProperty(col.field)" /></div>';

    var ContentCtrl = PymApp.controller('ContentCtrl',
            ['$scope',
    function ($scope) {

        $scope.entity_list = ${data|n};
        $scope.coldefs = ${coldefs|n};
        $scope.coldefs_by_field = {};
        angular.forEach($scope.coldefs, function(v, k) {
            this[v.field] = v;
        }, $scope.coldefs_by_field);
        console.log($scope.coldefs_by_field);

        $scope.crud_grid = {};
        $scope.crud_grid.selected = [];
        $scope.crud_grid.data = $scope.entity_list;
        $scope.crud_grid.columnDefs = $scope.coldefs;
        $scope.crud_grid.options = {
            data: 'entity_list',
            columnDefs: 'coldefs',
            selectedItems: $scope.crud_grid.selected,
            enablePinning: false,
            multiSelect: false,
            enableCellSelection: true,
            enableRowSelection: true,
            enableCellEdit: true,
            showColumnMenu: true,
            showFilter: true,
            showFooter: true,
            jqueryUITheme: false,
            plugins: []
        };
        $scope.crud_grid.columnDefs[1]['cellTemplate'] = checkbox_cell_template;
        $scope.crud_grid.columnDefs[2]['cellTemplate'] = checkbox_cell_template;
        $scope.entity = {};
    }]);

    return ContentCtrl;
});
</script>