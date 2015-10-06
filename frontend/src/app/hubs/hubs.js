angular.module( 'wikiaAuthority.hubs')
  .service( 'HubService',
    ['$http',
      function HubService($http){
        var hub_data = {};
        var get_hubs = function(callback) {
          $http.get('/api/hubs').success(callback)
        };
        return {
          get_hubs: get_hubs,
          hub_data: hub_data
        };
}])
.controller( 'HubsCtrl',
['$scope', 'HubService',
  function HubsController( $scope, HubService ) {
    HubService.get_hubs(function(data) {
      $scope.hubs = [];
      data.forEach(function(datum) {
        HubService.hub_data[datum.hub] = true;
        $scope.hubs.push(datum.hub);
      });
      $scope.hub_data = HubService.hub_data;
    });
  }
]);

