function CreateWalletController($scope, $http, $location, $modalInstance, userService) {
  $scope.createWallet = function(create) {
    if(create.password != create.repeatPassword) {
      console.log("Passwords don't match")
      $scope.passwordCompare = true;
    } else {
      var uuid = generateUUID();
      var password = create.password;
      var ecKey = new Bitcoin.ECKey();
      var address = ecKey.getBitcoinAddress().toString();
      var encryptedPrivateKey = ecKey.getEncryptedFormat(password);

      var wallet = {
        email: create.email,
        uuid: uuid,
        addresses: [{
          address: address,
          privkey: encryptedPrivateKey
        }]
      };

      syncWallet($scope, $http, $location, $modalInstance, userService, wallet, address, encryptedPrivateKey);
    }
  }
}

function syncWallet($scope, $http, $location, $modalInstance, userService, wallet) {
  // Strange serialization effects, stringifying wallet initially
  var postData = {
    type: 'SYNCWALLET',
    wallet: JSON.stringify(wallet)
  };
  $http({
    url: '/v1/user/wallet/sync/',
    method: 'POST',
    data: postData,
    headers: {'Content-Type': 'application/json'}
  })
  .success(function(data, status, headers, config) {
    console.log("Success");
    userService.login(wallet);
    $modalInstance.close();
    $location.path("/wallet");
  })
  .error(function(data, status, headers, config) {
    console.log("Error on login");
    $scope.serverError = true;
  });
}

function generateUUID() {
  var d = new Date().getTime();
  var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    var r = (d + Math.random() * 16) % 16 | 0;
    d = Math.floor(d / 16);
    return (c == 'x' ? r : (r & 0x7 | 0x8)).toString(16);
  });
  return uuid;
};

