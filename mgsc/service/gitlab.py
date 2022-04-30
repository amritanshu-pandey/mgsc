from mgsc.service.service import GitService
from mgsc.blueprints import Repository, Namespace


class Gitlab(GitService):
    @property
    def servertype(self):
        return "gitlab"

    def get_paginated(self, path):
        response = self.session.httpaction(http_verb="get", path=path)
        number_of_pages = int(response.headers["x-total-pages"])
        for page in range(1, number_of_pages + 1):
            response = self.session.httpaction(
                http_verb="get", path=f"{path}?page={page}"
            ).json()

            for item in response:
                yield item

    @property
    def repositories(self) -> Repository:
        all_repos = self.session.httpaction(
            http_verb="get", path=f"/users/{self.userid}/projects?per_page=50000"
        ).json()

        for repo in all_repos:
            yield Repository(
                name=repo["name"],
                namespace=Namespace(repo["namespace"]["path"]),
                ssh_url=repo["ssh_url_to_repo"],
                http_url=repo["http_url_to_repo"],
                localfs_url=None,
                description=repo["description"],
            )

    def get_namespace_repos(self, namespace_id):
        namespace_dict = self.session.httpaction(
            "get", f"/namespaces/{namespace_id}"
        ).json()

        if namespace_dict["kind"] == "user":
            for repo in self.repositories:
                yield repo
        else:
            group_projects = self.get_paginated(f"/groups/{namespace_id}/projects")

            for repo in group_projects:
                repo_obj = Repository(
                    name=repo["name"],
                    namespace=self.get_namespace(namespace_id),
                    ssh_url=repo["ssh_url_to_repo"],
                    http_url=repo["http_url_to_repo"],
                    localfs_url=None,
                    description=repo["description"],
                )
                repo_obj.raw = repo
                yield repo_obj

    def get_namespaces(self) -> Namespace:
        namespaces = self.session.httpaction(
            http_verb="get", path=f"/namespaces/"
        ).json()

        for ns in namespaces:
            namespace_obj = Namespace(
                name=ns["path"], parent=ns["parent_id"], id=ns["id"]
            )
            namespace_obj.path = ns["full_path"]
            namespace_obj.repositories = self.get_namespace_repos(ns["id"])
            yield namespace_obj

    def get_namespace(self, namespace_id: str) -> Namespace:
        ns = self.session.httpaction(
            http_verb="get", path=f"/namespaces/{namespace_id}"
        ).json()
        namespace_obj = Namespace(name=ns["path"], parent=ns["parent_id"], id=ns["id"])
        namespace_obj.repositories = self.get_namespace_repos(ns["id"])
        namespace_obj.raw = ns
        return namespace_obj

    @property
    def userid(self):
        userid = self.session.httpaction("get", "/user").json()["id"]
        return userid

    def create_namespace(self, name, parent_id=None, path=None, **kwargs):
        group = self.session.httpaction(
            http_verb="POST",
            path="/groups",
            xstatus=201,
            data={"name": name, "path": path or name, "parent_id": parent_id, **kwargs},
        )
        return group.json()

    def create_repository(self, name, namespace_id=None, **kwargs):
        repository = self.session.httpaction(
            http_verb="POST",
            path="/projects",
            xstatus=201,
            data={"name": name, "namespace_id": namespace_id, **kwargs},
        )
        return repository.json()
