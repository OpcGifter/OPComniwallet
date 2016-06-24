angular.module("omniFactories")
	.factory("Orderbook",["$http","DExOrder","DExOffer","Transaction","Account","Wallet","ModalManager","MIN_MINER_FEE", "WHOLE_UNIT", "SATOSHI_UNIT", 
		function OrderbookFactory($http,DExOrder,DExOffer,Transaction,Account,Wallet,ModalManager,MIN_MINER_FEE,WHOLE_UNIT,SATOSHI_UNIT){
			var Orderbook = function(tradingPair){
				var self = this;

				self.initialize = function(){
					self.tradingPair=tradingPair;
					self.title = "Trade " + tradingPair.selling.propertyName + " for " + tradingPair.desired.propertyName;
					self.active = true;
					self.disabled = !self.active;
					self.buyOrder = {};
					self.sellOrder = {};

					self.selling = tradingPair.selling;
					self.desired = tradingPair.desired;

					// TODO:  list only addresses with balance > 0
					self.addresses = Wallet.addresses.filter(function(address){
						return ((address.privkey && address.privkey.length == 58) || address.pubkey)
					});

					self.buyBook = []
					self.sellBook = []

					$http.get("/v1/markets/"+tradingPair.desired.propertyid+"/"+tradingPair.selling.propertyid)
						.then(function(response){
							if(response.status != "200" || response.data.status !="OK")
								return // handle errors

							
							var offers = response.data.orderbook
							offers.forEach(function(offerData){
								var order = null;
								var offer = new DExOffer(offerData);
								self.buyBook.forEach(function(orderData){
									if(orderData.price.eq(offer.price)){
										order = orderData;
										order.addOffer(offer)
									}
										
								})

								if(order == null){
									order = new DExOrder(offer);
									self.buyBook.push(order);
								}

							});

							self.buyBook.sort(function(a, b) {
					          var priceA = a.price;
					          var priceB = b.price;
					          return priceA.gt(priceB) ? -1 : priceA.lt(priceB) ? 1 : 0;
					        });
						})
					$http.get("/v1/markets/"+tradingPair.selling.propertyid+"/"+tradingPair.desired.propertyid)
						.then(function(response){
							if(response.status != "200" || response.data.status !="OK")
								return // handle errors

							
							var offers = response.data.orders
							offers.forEach(function(offerData){
								var order = null;
								var offer = new DExOffer(offerData);
								self.sellBook.forEach(function(orderData){
									if(orderData.price.eq(offer.price)){
										order = orderData;
										order.addOffer(offer)
									}
								})
								if(order == null){
									order = new DExOrder(offer);
									self.sellBook.push(order);
								}


							});

							self.sellBook.sort(function(a, b) {
					          var priceA = a.price;
					          var priceB = b.price;
					          return priceA.lt(priceB) ? -1 : priceA.gt(priceB) ? 1 : 0;
					        });
						})

				};

				self.submitBuyOffer = function(){
					// TODO: Validations
					var fee = Account.settings.minerFee || MIN_MINER_FEE;
					var dexOffer = new Transaction(25,self.buyOrder.address,fee,{
							transaction_version:0,
							propertyidforsale:self.tradingPair.desired.propertyid,
							amountforsale: self.tradingPair.desired.divisible ? new Big(self.sellOrder.amounts.desired).times(SATOSHI_UNIT).valueOf() : new Big(self.sellOrder.amounts.desired).valueOf(),
							propertiddesired:self.tradingPair.selling.propertyid,
							amountdesired: self.tradingPair.selling.divisible ? new Big(self.sellOrder.amounts.selling).times(SATOSHI_UNIT).valueOf() : new Big(self.sellOrder.amounts.selling).times(SATOSHI_UNIT).valueOf()
						});
					ModalManager.openConfirmationModal({
						dataTemplate: '/views/modals/partials/dex_offer.html',
						scope: {
							title:"Confirm DEx Transaction",
							address:self.buyOrder.address,
							saleCurrency:self.tradingPair.desired.propertyid,
							saleAmount:self.buyOrder.amounts.desired,
							desiredCurrency:self.tradingPair.selling.propertyid,
							desiredAmount:self.buyOrder.amounts.selling,
							totalCost:dexOffer.totalCost,
							action:"Add",
							confirmText: "Create Transaction",
							successMessage: "Your order was placed successfully"
						},
						transaction:dexOffer
					})
				};

				self.submitSellOffer = function(){
					// TODO: Validations
					var fee = Account.settings.minerFee || MIN_MINER_FEE;
					var dexOffer = new Transaction(25,self.sellOrder.address,fee,{
							transaction_version:0,
							propertyidforsale:self.tradingPair.selling.propertyid,
							amountforsale: self.tradingPair.selling.divisible ? new Big(self.sellOrder.amounts.selling).times(SATOSHI_UNIT).valueOf() : new Big(self.sellOrder.amounts.selling).valueOf(),
							propertiddesired:self.tradingPair.desired.propertyid,
							amountdesired: self.tradingPair.desired.divisible ? new Big(self.sellOrder.amounts.desired).times(SATOSHI_UNIT).valueOf() : new Big(self.sellOrder.amounts.desired).times(SATOSHI_UNIT).valueOf()
						});
					ModalManager.openConfirmationModal({
						dataTemplate: '/views/modals/partials/dex_offer.html',
						scope: {
							title:"Confirm DEx Transaction",
							address:self.sellOrder.address,
							saleCurrency:self.tradingPair.selling.propertyid,
							saleAmount:self.sellOrder.amounts.selling,
							desiredCurrency:self.tradingPair.desired.propertyid,
							desiredAmount:self.sellOrder.amounts.desired,
							totalCost:dexOffer.totalCost,
							action:"Add",
							confirmText: "Create Transaction",
							successMessage: "Your order was placed successfully"
						},
						transaction:dexOffer
					})
				};

				self.getBalance = function(address, assetId){
					return address && address.getBalance(assetId) ? new Big(address.getBalance(assetId).value).times(WHOLE_UNIT).valueOf() : 0;
				}

				self.initialize();
			}

			return Orderbook;
		}]);