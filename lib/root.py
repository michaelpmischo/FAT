#!/usr/bin/env python3
import data, sector, cluster, directory


# =============================================================================
# RootDirectory16
# -----------------------------------------------------------------------------
#
#
# =============================================================================
class RootDirectory(directory.Directory):
    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 offset_in: int, size_in: int):
        super().__init__(data_in, endianness_in, offset_in, size_in)
        self.DIR_Attr = self.ATTR_VOLUME_ID


# =============================================================================
# RootDirectory16
# -----------------------------------------------------------------------------
#
#
# =============================================================================
class RootDirectory16(sector.Sector, RootDirectory):
    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 sector_in: int = 0, size_in: int = int(0.5 * data.Data._KiB)):
        sector.Sector.__init__(self, data_in, endianness_in, sector_in, size_in)
        RootDirectory.__init__(self, data_in, endianness_in, self.offset, 16)
        self.DIR_Attr = self.ATTR_VOLUME_ID


# =============================================================================
# RootDirectory32
# -----------------------------------------------------------------------------
#
#
# =============================================================================
class RootDirectory32(cluster.Cluster, RootDirectory):
    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 cluster_in: int, number_of_sectors_in: int,
                 sector_size_in: int = int(0.5 * data.Data._KiB)):
        cluster.Cluster.__init__(
            self, data_in, endianness_in, cluster_in, number_of_sectors_in, sector_size_in)
        RootDirectory.__init__(self, data_in, endianness_in, self.offset, 32)
        self.DIR_Attr = self.ATTR_VOLUME_ID
