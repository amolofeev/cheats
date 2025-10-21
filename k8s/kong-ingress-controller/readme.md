Все `yaml` имеют комменты
- установка не достающих CRDs (GatewayClass, Gateway, HTTPRoute)
  - `kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.0.0/standard-install.yaml`
- установка kong
  - `helm install kong kong/kong -f kong-values.yaml`
- установка jaeger (необязательно) + конфиги для kong
  - `kubectl apply -f jaeger.yaml`
  - перезапустить kong
- тестовый сервис + основа настройки маршрутизации
  - `kubectl apply -f test-service.yaml`
