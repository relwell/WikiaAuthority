angular.module( 'wikiaAuthority.hubs')
  .service( 'HubsService',
    ['$http',
      function HubsService($http){
        var hub_data = {};
        var get_hubs = function(callback) {
          $http.get('/api/hubs').success(callback)
        };
        var params = function(other_params) {
          // todo: implement, durr
          return other_params;
        };
        return {
          get_hubs: get_hubs,
          hub_data: hub_data,
          hub_params: params
        };
}])
.controller( 'HubsCtrl',
['$scope', 'HubsService',
  function HubsController( $scope, HubsService ) {
    HubsService.get_hubs(function(data) {
      $scope.hubs = [];
      data.forEach(function(datum) {
        HubsService.hub_data[datum.hub] = true;
        $scope.hubs.push(datum.hub);
      });
      $scope.hub_data = HubService.hub_data;
    });
  }
]);

