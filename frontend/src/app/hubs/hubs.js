angular.module( 'wikiaAuthority.hubs', [])
.service( 'HubsService',
  ['$http', '$location',
    function HubsService($http, $location){
      var selected_hub = null;

      var get_selected_hub = function get_selected_hub() {
        selected_hub = $location.search().hub || '';
        return selected_hub;
      };

      var get_hubs = function(callback) {
        $http.get('/api/hubs').success(callback);
      };

      var params = function(other_params) {
        other_params = other_params || {};
        get_selected_hub();
        if (selected_hub && selected_hub !== 0 && selected_hub !== '0') {
          other_params['fq'] = "hub_s:"+selected_hub;
        }
        return other_params;
      };

      return {
        get_hubs: get_hubs,
        selected_hub: selected_hub,
        params: params,
        get_selected_hub: get_selected_hub
      };
}])
.controller( 'HubsCtrl',
['$scope', '$location', 'HubsService',
  function HubsController( $scope, $location, HubsService ) {
    $scope.selected_hub = HubsService.get_selected_hub();
    HubsService.get_hubs(function(data) {
      $scope.hubs = [];
      data.forEach(function(datum) {
        $scope.hubs.push(datum.hub);
      });
    });
    $scope.$watch('selected_hub', function() {
      HubsService.selected_hub = $scope.selected_hub;
      if ($location.search().hub !== HubsService.selected_hub) {
        $location.search('hub', $scope.selected_hub);
      }
    });

    $scope.$on('$locationChangeSuccess', HubsService.get_selected_hub);
  }
]);

