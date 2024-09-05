
class VMTags():
    def __init__(self, tags=None):
        self.tags = tags if tags else {}

    def get_tag(self, key):
        return self.tags.get(key)

    def get_tags(self):
        return self.tags

    def get_node(self):
        return self.tags.get('node')

    def get_role(self):
        return self.tags.get('role')

    def get_cluster_name(self):
        return self.tags.get('cname')

    def get_vm_name(self):
        return self.tags.get('vm')

    def get_version(self):
        return self.tags.get('ver')

    def get_cluster_id(self):
        return self.tags.get('cid')

    def get_allocation(self):
        return self.tags.get('allocation')

    def get_all_tags(self):
        return self.tags

    def set_tags(self, tags):
        self.tags = tags
        return self

    def set_tag(self, key, value):
        self.tags[key] = value
        return self

    def set_node(self, node):
        self.tags['node'] = node
        return self

    def set_role(self, role):
        self.tags['role'] = role
        return self

    def set_cluster_name(self, cluster_name):
        self.tags['cname'] = cluster_name
        return self

    def set_vm_name(self, name):
        self.tags['vm'] = name
        return self

    def set_cluster_id(self, cluster_id):
        self.tags['cid'] = cluster_id
        return self

    def set_version(self, version):
        self.tags['ver'] = version
        return self

    def set_allocation(self, allocation):
        self.tags['allocation'] = allocation
        return self

    def str(self):
        return ';'.join([f"{key}.{value}" for key, value in self.tags.items()])

    def __str__(self):
        return self.str()

    def __repr__(self):
        return self.str()

    def __eq__(self, other):
        return self.tags == other.get_tags()

    def __ne__(self, other):
        return self.tags != other.get_tags()

    def is_subset(self, other):
        return all([self.get_tag(key) == other.get_tag(key) for key in self.tags.keys()])

    # def construct_vm_tags(node, cluster_name, cluster_id, server_name, unique_id):
    #     return f"node.{node},cname.{cluster_name},sname.{server_name},cid.{cluster_id},allocation.{unique_id}"

    @staticmethod
    def parse_tags(tags):
        """get representation of tags as string and return dict format"""
        splitted = tags.split(';')
        new_tags = VMTags()
        for tag in splitted:
            if len(tag.split('.')) == 2:
                key, value = tag.split('.')
                new_tags.set_tag(key, value)
        return new_tags


