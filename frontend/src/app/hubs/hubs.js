angular.module( 'wikiaAuthority.hubs')
  .service( 'HubsService',
    ['$http',
      function HubsService($http){
        var selected_hub = null;
        var get_hubs = function(callback) {
          $http.get('/api/hubs').success(callback)
        };
        var params = function(other_params) {
          other_params = other_params || {};
          if (selected_hub && selected_hub !== 0 && selected_hub !== '0') {
            other_params['fq'] = "hub_s:"+selected_hub;
          }
          return other_params;
        };
        return {
          get_hubs: get_hubs,
          selected_hub: selected_hub,
          hub_params: params
        };
}])
.controller( 'HubsCtrl',
['$scope', '$location', 'HubsService',
  function HubsController( $scope, $location, HubsService ) {
    $scope.selected_hub = HubsService.selected_hub;
    HubsService.get_hubs(function(data) {
      $scope.hubs = [];
      data.forEach(function(datum) {
        $scope.hubs.push(datum.hub);
      });
    });
    $scope.watch('selected_hub', function() {
      HubsService.selected_hub = $scope.selected_hub;
      $location.search('hub', $scope.selected_hub)
    });

    $scope.$on('$locationChangeSuccess', function() {
      $scope.selected_hub = $location.search('hub');
    });
  }
]);

