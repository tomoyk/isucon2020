# isucon2020

isucon10 (2020)の反省会

## Usage

1. Create containers by docker-compose

```
docker-compose up -d --build
```

2. Access http://localhost:8000/ on your browser.

```
curl http://localhost:8000/
```

3. Check initialize api endpoint.

```
curl -XPOST http://localhost:8000/initialize
```
