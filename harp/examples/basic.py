from harp import ProxyFactory

proxy = ProxyFactory(
    settings={
        # "storage": {
        #     "type": "sql_database",
        # }
    }
)

proxy.add("https://api-adresse.data.gouv.fr/", port=4000, name="api-adresse")
proxy.add("https://api-adresse.data.gouv.fr/", port=4001, name="api-adresse (2)")

if __name__ == "__main__":
    proxy.run()
