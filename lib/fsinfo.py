#!/usr/bin/env python3
import struct
import sector


# =============================================================================
# File System Information (FSInfo)
# -----------------------------------------------------------------------------
# The File System Information (FSInfo) structure helps optimize file system
# driver implementations by containing a count of the number of free clusters
# on the volume as well as the cluster number for the first available (free)
# cluster.
#
# NOTE: The information contained in the structure must be considered as
# advisory only and file system driver implementations must validate the
# values at volume mount. File system driver implementations are not required
# to ensure that information within the structure is kept consistent although
# this is recommended.
#
# The FSInfo structure is only present on volumes formatted FAT32. The
# structure must be persisted on the media during volume initialization
# (format). The structure must be located at sector #1 – immediately following
# the sector containing the BPB.
#
# A copy of the structure is maintained at sector #7.
#
# =============================================================================
class FSInfo(sector.Sector):
    """
    The File System Information (FSInfo) structure helps optimize file
    system driver implementations by containing a count of the number
    of free clusters on the volume as well as the cluster number for
    the first available (free) cluster.

    NOTE: The information contained in the structure must be considered
    as advisory only and file system driver implementations must
    validate the values at volume mount. File system driver
    implementations are not required to ensure that information within
    the structure is kept consistent although this is recommended.

    The FSInfo structure is only present on volumes formatted FAT32.
    The structure must be persisted on the media during volume
    initialization (format). The structure must be located at sector #1
    – immediately following the sector containing the BPB.

    A copy of the structure is maintained at sector #7.
    """
    LEAD_SIGNATURE = 0x41615252
    STRUC_SIGNATURE = 0x61417272
    TRAIL_SIGNATURE = 0xAA550000

    # The value 0xFFFFFFFF indicates the free count is not known.
    UNKNOWN = 0xFFFFFFFF

    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 sector_in: int, size_in: int):
        super().__init__(data_in, endianness_in, sector_in, size_in)

    def format(self, clusters_in: int = None, first_free_in: int = None):
        # This lead signature is used to validate the beginning of the FSInfo
        # structure in the sector. Must be 0x52521641
        self.FSI_LeadSig = self.LEAD_SIGNATURE

        # An additional signature validating the integrity of the FSInfo
        # structure. Must be 0x61417272
        self.FSI_StrucSig = self.STRUC_SIGNATURE

        # Contains the last known free cluster count on the
        # volume. At format the free count is unknown.
        if clusters_in is None:
            self.FSI_Free_Count = self.UNKNOWN
        else:
            self.FSI_Free_Count = clusters_in

        # Contains the cluster number of the first available
        # (free) cluster on the volume.
        if first_free_in is None:
            self.FSI_Nxt_Free = self.UNKNOWN
        else:
            self.FSI_Nxt_Free = first_free_in

        # This trail signature is used to validate the integrity of the data in
        # the sector containing the FSInfo structure. Must be 0xAA550000
        self.FSI_TrailSig = self.TRAIL_SIGNATURE

    @property
    def FSI_LeadSig(self) -> int:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_LeadSig      | 0                 | 4             |
        ------------------------------------------------------
        Value = 0x41615252. This lead signature is used to validate
        the beginning of the FSInfo structure in the sector.

        :return: int: 0x41615252
        """
        return struct.unpack_from(
            f"{self.endianness}L",
            self.data, 0)[0]

    @FSI_LeadSig.setter
    def FSI_LeadSig(self, signature_in: int):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_LeadSig      | 0                 | 4             |
        ------------------------------------------------------
        Value = 0x41615252. This lead signature is used to validate
        the beginning of the FSInfo structure in the sector.

        :param signature_in: int: 0x41615252
        """
        if signature_in == self.LEAD_SIGNATURE or signature_in == 0:
            struct.pack_into(
                f"{self.endianness}L", self.data,
                0, signature_in)
        else:
            raise ValueError(
                f"Error: Invalid FSI_LeadSig: {signature_in}\n"
                f"Must Be: {self.LEAD_SIGNATURE} or 0.")

    @property
    def FSI_Reserved1(self) -> memoryview:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_Reserved1     | 4                | 480           |
        ------------------------------------------------------
        Reserved. Must be set to 0.

        :return: memoryview:
        """
        return self.data[4:484]

    @property
    def FSI_StrucSig(self) -> int:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_StrucSig      | 484              | 4             |
        ------------------------------------------------------
        Value = 0x61417272. An additional signature validating the
        integrity of the FSInfo structure.

        :return: int: 0x61417272
        """
        return struct.unpack_from(
            f"{self.endianness}L",
            self.data, 484)[0]

    @FSI_StrucSig.setter
    def FSI_StrucSig(self, signature_in: int):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_StrucSig      | 484              | 4             |
        ------------------------------------------------------
        Value = 0x61417272. An additional signature validating the
        integrity of the FSInfo structure.

        :param signature_in: int: 0x61417272
        """
        if signature_in == self.STRUC_SIGNATURE or signature_in == 0:
            struct.pack_into(
                f"{self.endianness}L", self.data,
                484, signature_in)
        else:
            raise ValueError(
                f"Error: Invalid FSI_StrucSig: {signature_in}\n"
                f"Must Be: {self.STRUC_SIGNATURE} or 0.")

    @property
    def FSI_Free_Count(self) -> int:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_Free_Count    | 488              | 4             |
        ------------------------------------------------------
        Contains the last known free cluster count on the volume. The
        value 0xFFFFFFFF indicates the free count is not known. The
        contents of this field must be validated at volume mount (and
        subsequently maintained in memory by the file system driver
        implementation). It is recommended that this field contain an
        accurate count of the number of free clusters at volume
        dismount (during controlled dismount/shutdown).

        :return: int: The last known free cluster count on the volume.
        """
        return struct.unpack_from(
            f"{self.endianness}L",
            self.data, 488)[0]

    @FSI_Free_Count.setter
    def FSI_Free_Count(self, count_in: int):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_Free_Count    | 488              | 4             |
        ------------------------------------------------------
        Contains the last known free cluster count on the volume. The
        value 0xFFFFFFFF indicates the free count is not known. The
        contents of this field must be validated at volume mount (and
        subsequently maintained in memory by the file system driver
        implementation). It is recommended that this field contain an
        accurate count of the number of free clusters at volume
        dismount (during controlled dismount/shutdown).

        :param count_in: int: The last known free cluster count on the volume.
        """
        struct.pack_into(
            f"{self.endianness}L", self.data,
            488, count_in)

    @property
    def FSI_Nxt_Free(self) -> int:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_Nxt_Free      | 492              | 4             |
        ------------------------------------------------------
        Contains the cluster number of the first available (free)
        cluster on the volume. The value 0xFFFFFFFF indicates that
        there exists no information about the first available (free)
        cluster.
        The contents of this field must be validated at volume mount.
        It is recommended that this field be appropriately updated at
        volume dismount (during controlled dismount/shutdown).

        :return: int: The cluster number of the first available (free)
        cluster on the volume.
        """
        return struct.unpack_from(
            f"{self.endianness}L",
            self.data, 492)[0]

    @FSI_Nxt_Free.setter
    def FSI_Nxt_Free(self, cluster_in: int):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_Nxt_Free      | 492              | 4             |
        ------------------------------------------------------
        Contains the cluster number of the first available (free) cluster on
        the volume. The value 0xFFFFFFFF indicates that there exists no
        information about the first available (free) cluster.
        The contents of this field must be validated at volume mount. It is
        recommended that this field be appropriately updated at volume dismount
        (during controlled dismount/shutdown).

        :param cluster_in: int: The cluster number of the first available
        (free) cluster on the volume.
        """
        struct.pack_into(
            f"{self.endianness}L", self.data,
            492, cluster_in)

    @property
    def FSI_Reserved2(self) -> memoryview:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_StrucSig      | 496              | 12            |
        ------------------------------------------------------
        Reserved. Must be set to 0.

        :return memoryview: Must be set to 0.
        """
        return self.data[496:508]

    @property
    def FSI_TrailSig(self) -> int:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_StrucSig      | 508              | 4             |
        ------------------------------------------------------
        Value = 0xAA550000. This trail signature is used to validate
        the integrity of the data in the sector containing the FSInfo
        structure.

        :return: int: Shall be 0xAA550000.
        """
        return struct.unpack_from(
            f"{self.endianness}L",
            self.data, 508)[0]

    @FSI_TrailSig.setter
    def FSI_TrailSig(self, signature_in: int):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_StrucSig      | 508              | 4             |
        ------------------------------------------------------
        Value = 0xAA550000. This trail signature is used to validate
        the integrity of the data in the sector containing the FSInfo
        structure.

        :param signautre_in: int: Shall be 0xAA550000.
        """
        if signature_in == self.TRAIL_SIGNATURE or signature_in == 0:
            struct.pack_into(
                f"{self.endianness}L", self.data,
                508, signature_in)
        else:
            raise ValueError(
                f"Error: Invalid FSI_TrailSig: {signature_in}\n"
                f"Must Be: {self.STRUCT_SIGNATURE} or 0.")

    @property
    def valid(self) -> bool:
        """
        Compare the structure's signatures to validate the integrity of
        the data in the sector containing the FSInfo structure.

        :return: True if all signatures are correct, else False.
        """
        return (self.FSI_LeadSig == self.LEAD_SIGNATURE and
                self.FSI_StrucSig == self.STRUC_SIGNATURE and
                self.FSI_TrailSig == self.TRAIL_SIGNATURE)