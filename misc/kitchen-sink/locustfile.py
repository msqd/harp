from locust import HttpUser, task, between
import random

AVERAGE_WAIT_TIME = 5.0

PORTS = (
    "4000",
    "4001",
)


class BinUser(HttpUser):
    wait_time = between(AVERAGE_WAIT_TIME * 0.5, AVERAGE_WAIT_TIME * 1.5)

    def _get_host(self):
        host = self.host
        if host.endswith(":4000"):
            host = host[:-5] + ":" + random.choice(PORTS)
        return host

    def get(self, path, *args, **kwargs):
        return self.client.get(self._get_host() + path, *args, **kwargs)

    def post(self, path, *args, **kwargs):
        return self.client.post(self._get_host() + path, *args, **kwargs)

    def put(self, path, *args, **kwargs):
        return self.client.put(self._get_host() + path, *args, **kwargs)

    def patch(self, path, *args, **kwargs):
        return self.client.patch(self._get_host() + path, *args, **kwargs)

    def delete(self, path, *args, **kwargs):
        return self.client.delete(self._get_host() + path, *args, **kwargs)

    @task
    def cached(self):
        self.get("/cache/" + str(random.randint(10, 20) * 60))

    @task
    def simple_get(self):
        self.get(random.choice(["/", "/get", "/xml", "/json"]))

    @task
    def simple_post(self):
        self.post("/post")

    @task
    def simple_put(self):
        self.put("/put")

    @task
    def simple_patch(self):
        self.patch("/patch")

    @task
    def simple_delete(self):
        self.delete("/delete")

    @task
    def delay(self):
        self.get("/delay/" + str(random.randint(1, 10)))

    @task
    def custom_status(self):
        self.get("/status/" + random.choice(["200", "201", "202", "204", "400", "401", "403", "404", "500"]))

    @task
    def image(self):
        self.get("/image" + random.choice(["", "/jpeg", "/png", "/svg", "/webp"]))


if __name__ == "__main__":
    from locust import run_single_user

    run_single_user(BinUser)
