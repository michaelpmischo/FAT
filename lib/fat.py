#!/usr/bin/env python3
import struct, math
from abc import ABC, abstractmethod
import data


# =============================================================================
# FAT Entry
# -----------------------------------------------------------------------------
# Each valid entry in the File Allocation Table (FAT) represents the state of a
# cluster from the set of clusters comprising the Root Directory Region (when
# applicable) and the File and Directory Data Region. The size of each (packed)
# entry in the FAT is as follows:
#   - For FAT12 volumes, each FAT entry is 12 bits in length
#   - For FAT16 volumes, each FAT entry is 16 bits in length
#   - For FAT32 volumes, each FAT entry is 32 bits in length
# As stated earlier, a FAT may be larger than that required to describe all
# allocatable sectors comprising the Root/Data regions. Extra entries in the
# FAT (located at the tail/end of the FAT) must be set to a value of 0.
#
# =============================================================================
class FATEntry(data.Data, ABC):
    """
    Each valid entry in the File Allocation Table (FAT) represents the state
    of a cluster from the set of clusters comprising the Root Directory Region
    (when applicable) and the File and Directory Data Region. The size of each
    (packed) entry in the FAT is as follows:
      - For FAT12 volumes, each FAT entry is 12 bits in length
      - For FAT16 volumes, each FAT entry is 16 bits in length
      - For FAT32 volumes, each FAT entry is 32 bits in length
    As stated earlier, a FAT may be larger than that required to describe all
    allocatable sectors comprising the Root/Data regions. Extra entries in the
    FAT (located at the tail/end of the FAT) must be set to a value of 0.

    The FAT defines a singly linked list of the “extents” (clusters) of a file
    and thereby maps the data region of the volume by cluster number. The first
    data cluster in the volume is cluster #2

    NOTE: A FAT directory or file container is simply a regular file with a
    special attribute indicating the directory type. The contents of the
    directory are a series of 32 byte directory entries (described in Section
    6).
    """
    LENGTH = 0

    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 offset_in: int = 0x00000000, length_in: int = 4):
        super().__init__(data_in, endianness_in, offset_in, math.ceil(length_in / 8))

    @property
    @abstractmethod
    def length(self) -> int:
        pass

    @property
    def next(self) -> int:
        return self.value

    @property
    @abstractmethod
    def free(self) -> bool:
        pass

    @property
    @abstractmethod
    def bad(self) -> bool:
        pass

    @property
    @abstractmethod
    def end(self) -> bool:
        pass

    @property
    @abstractmethod
    def value(self) -> int:
        pass

    @value.setter
    @abstractmethod
    def value(self, value_in: int):
        pass

    @abstractmethod
    def __sizeof__(self) -> int:
        pass


# =============================================================================
# FAT12 Entry
# -----------------------------------------------------------------------------
# The size of the FAT is limited to 6K sectors on volumes formatted FAT12.
#
# TODO: This doesn't yet work...
# =============================================================================
class FATEntry12(FATEntry):
    """
    The size of the FAT is limited to 6K sectors on volumes formatted FAT12.
    """
    LENGTH = 1.5

    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 offset_in: int = 0x00000000):
        super().__init__(data_in, endianness_in, offset_in, 12)

    @property
    def length(self) -> int:
        return self.LENGTH

    @property
    def free(self) -> bool:
        return self.value == 0x000

    @property
    def bad(self) -> bool:
        return self.value == 0xFF7

    @property
    def end(self) -> bool:
        return self.value == 0xFFF

    @property
    def value(self) -> int:
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 0)[0] & 0x0FFF

    @value.setter
    def value(self, value_in: int):
        struct.pack_into(
            f"{self.endianness}H", self.data,
            0, value_in & 0x0FFF)

    def __sizeof__(self) -> int:
        return self.length


# =============================================================================
# FAT16 Entry
# -----------------------------------------------------------------------------
# The size of the FAT is limited to 128K sectors on volumes formatted FAT16.
#
# =============================================================================
class FATEntry16(FATEntry):
    """
    The size of the FAT is limited to 128K sectors on volumes formatted FAT16.
    """
    LENGTH = struct.calcsize("H")

    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 offset_in: int = 0x00000000):
        super().__init__(data_in, endianness_in, offset_in, 16)

    @property
    def length(self) -> int:
        return self.LENGTH

    @property
    def free(self) -> bool:
        return self.value == 0x0000

    @property
    def bad(self) -> bool:
        return self.value == 0xFFF7

    @property
    def end(self) -> bool:
        return self.value == 0xFFFF

    @property
    def value(self) -> int:
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 0)[0]

    @value.setter
    def value(self, value_in: int):
        struct.pack_into(
            f"{self.endianness}H", self.data,
            0, value_in & 0xFFFF)

    def __sizeof__(self) -> int:
        return self.length


# =============================================================================
# FAT16 Entry
# -----------------------------------------------------------------------------
# There is no limit on the size of the FAT on volumes formatted FAT32.
#
# =============================================================================
class FATEntry32(FATEntry):
    """
    NOTE: The high 4 bits of a FAT32 FAT entry are reserved. All FAT
    implementations mus preserve the current value of the high 4 bits when
    modifying any FAT32 FAT entry except during volume initialization
    (formatting) when the entire FAT table must be set to 0.

    No FAT32 volume should ever be configured containing cluster numbers
    available for allocation >= 0xFFFFFF7.

    There is no limit on the size of the FAT on volumes formatted FAT32.
    """
    LENGTH = struct.calcsize("L")

    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 offset_in: int = 0x00000000):
        super().__init__(data_in, endianness_in, offset_in, 32)

    @property
    def length(self) -> int:
        return self.LENGTH

    @property
    def free(self) -> bool:
        return self.value == 0x00000000

    @property
    def bad(self) -> bool:
        return self.value == 0x0FFFFFF7

    @property
    def end(self) -> bool:
        return self.value == 0x0FFFFFFF

    @property
    def value(self) -> int:
        return struct.unpack_from(
            f"{self.endianness}L",
            self.data, 0)[0] & 0x0FFFFFFF

    @value.setter
    def value(self, value_in: int):
        struct.pack_into(
            f"{self.endianness}L", self.data,
            0, value_in & 0x0FFFFFFF)

    def __sizeof__(self) -> int:
        return self.length


# =============================================================================
# FAT (File Allocation Table)
# -----------------------------------------------------------------------------
# Each valid entry in the File Allocation Table (FAT) represents the state of a
# cluster from the set of clusters comprising the Root Directory Region (when
# applicable) and the File and Directory Data Region.
#
# As stated earlier, a FAT may be larger than that required to describe all
# allocatable sectors comprising the Root/Data regions. Extra entries in the
# FAT (located at the tail/end of the FAT) must be set to a value of 0.
#
# The FAT defines a singly linked list of the “extents” (clusters) of a file
# and thereby maps the data region of the volume by cluster number. The first
# data cluster in the volume is cluster #2.
#
# =============================================================================
class FAT(data.Data):

    __BITS = {
        # If bit is 1, the volume is “clean”. The volume can be mounted for
        # access. If bit is 0, the volume is “dirty” indicating that a FAT
        # file system driver was unable to dismount the volume properly
        # (during a prior mount operation). The volume contents should be
        # scanned for any damage to file system metadata.
        "CLnShutBitMask": {
            16: 0x8000,
            32: 0x08000000,
        },

        # If this bit is 1, no disk read/write errors were encountered.
        # If this bit is 0, the file system driver implementation
        # encountered a disk I/O error on the volume the last time it was
        # mounted, which is an indicator that some sectors may have gone
        # bad. The volume contents should be scanned with a disk repair
        # utility that does surface analysis on it looking for new bad
        # sectors.
        "HrdErrBitMask": {
            16: 0x4000,
            32: 0x04000000,
        },
    },

    __EOC = 0xFFFFFFFF
    __EOF = 0x0FFFFFF8

    def __init__(self, clusters_in: int, data_in: bytearray | memoryview,
                 endianness_in: str, offset_in: int, sector_size_in: int,
                 sectors_per_cluster_in: int, table_number_in: int = 1):
        super().__init__(data_in, endianness_in, offset_in)

        # Each implementation must determine the value for the last valid
        # sector in the FAT using CountOfClusters (the last valid sector in the
        # FAT is the one containing the FAT entry numbered CountOfClusters + 1).
        self.__clusters = clusters_in + 1
        self.__sector_size = sector_size_in
        self.__sectors_per_cluster = sectors_per_cluster_in
        self.__table = table_number_in

        # The FAT defines a singly linked list of the “extents” (clusters) of a
        # file and thereby maps the data region of the volume by cluster number.
        # The first data cluster in the volume is cluster #2.
        if self.__clusters < 4085:
            self.__fat = [
                FATEntry12(
                    data_in, endianness_in,
                    self.offset + cluster * FATEntry12.LENGTH)
                for cluster in range(self.__clusters)]

        elif self.__clusters < 65524:
            self.__fat = [
                FATEntry16(
                    data_in, endianness_in,
                    self.offset + cluster * FATEntry16.LENGTH)
                for cluster in range(self.__clusters)]

        else:
            self.__fat = [
                FATEntry32(
                    data_in, endianness_in,
                    self.offset + cluster * FATEntry32.LENGTH)
                for cluster in range(self.__clusters)]

        # Set the final size of the data buffer.
        self.size = self.__clusters * self.__fat[0].length

    def format(self, media_in: int = 0xF8):
        # The first two entries in the FAT are reserved.
        # The first reserved entry (FAT[0]), contains the BPB_Media byte value
        # in its low 8 bits, and all other bits are set to 1. For example, if
        # the BPB_Media value is 0xF8, then:
        self[0] = 0x0FFFFF00 | (media_in & 0x000000FF)
        self[1] = self.__EOC

        # Cluster is allocated and is the final cluster for the file (indicates
        # end-of-file).
        self[-1] = self.__EOF

        # Set all other entries to 0x0.
        for  entry in self.__fat[2:-1]:
            entry.value = 0x00000000

    def allocate(self, size_in: int = None) -> int:
        # Allocate the clusters.
        first, second = self.next_free
        if size_in is not None and size_in > self.cluster_size:
            self[first].value = second
            self.allocate(size_in - self.cluster_size)
        else:
            self[first].value = self.__EOF
        return first

    @property
    def first_free(self) -> int | None:
        for cluster, entry in enumerate(self.__fat):
            if entry.free:
                return cluster
        else:
            return None

    @property
    def next_free(self) -> tuple[int, int]:
        first = None
        for cluster, entry in enumerate(self.__fat):
            if entry.free:
                if first is not None:
                    return first, cluster
                else:
                    first = cluster
        else:
            return first, None

    @property
    def free_count(self) -> int:
        return len([entry for entry in self.__fat if entry.free])

    @property
    def sector_size(self) -> int:
        return self.__sector_size

    @property
    def cluster_size(self) -> int:
        return self.__sector_size * self.__sectors_per_cluster

    def __len__(self) -> int:
        return self.__size

    def __iter__(self):
        return iter(self.__fat)

    def __getitem__(self, cluster_in: int) -> FATEntry:
        """
        Given any valid cluster number N, this section describes the
        algorithm used to determine the entry in the FAT(s) for that cluster
        number.

        :return: FATEntry: The FAT entry for the cluster requested.
        """
        try:
            return self.__fat[cluster_in]
        except IndexError as _:
            raise ValueError(
                f"Cluster: {cluster_in} does not exist in the FAT.")

    def __setitem__(self, cluster_in: int, value_in: int | FATEntry):
        try:
            if isinstance(value_in, int):
                self.__fat[cluster_in].value = value_in
            elif isinstance(value_in, FATEntry):
                if value_in.size == self.__entry_size:
                    self.__fat[cluster_in] = value_in
                else:
                    raise ValueError(
                        f"Error: Invalid FAT Entry: {type(value_in).__name__}\n"
                        f"Expected: {type(self.__fat[cluster_in]).__name__}")
            else:
                raise ValueError(
                    f"Error: Invalid FATEntry: {type(value_in).__name__}")
        except IndexError as _:
            raise ValueError(
                f"Error: Cluster: {cluster_in} does not exist in the FAT.")


