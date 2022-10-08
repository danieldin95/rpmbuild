# rpmbuild
This project keep packages for unmaintain centos.

## Install deps
```
$ yum-builddep ./SPECS/libvirt.spec
```

## Build rpms
```
$ rpmbuild -ba ./SPECS/libvirt.spec
```
