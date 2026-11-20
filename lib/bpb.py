#!/usr/bin/env python3
import struct, math
from abc import ABC, abstractmethod
import data, sector, directory


# =============================================================================
# BIOS Parameter Block (BPB) structure common to FAT12, FAT16, and FAT32
# -----------------------------------------------------------------------------
# The BPB (BIOS Parameter Block) is located in the first sector of the volume
# in the Reserved Region. This sector is sometimes called the “boot sector” or
# the “0 th sector”. The important fact to note is that this sector is simply
# the first sector of the volume. All FAT volumes must have a BPB in the boot
# sector. The BPB has evolved over the years as follows:
#   • The FAT implementation in MS-DOS 1.x did not include a BPB (introduced
#     in MS-DOS 2.x)
#   • The BPB in MS-DOS 3.x was modified to allow > 64K sectors
#   • For FAT32, the BPB differs from that for FAT16/FAT12 beginning at offset
#     36
#
# The BPB in the boot sector of a FAT volume must always have all of the BPB
# fields for either the FAT12/FAT16 or FAT32 BPB type. This ensures maximum
# compatibility of the FAT volume and will also ensure that all FAT file
# system drivers understand and support the volume correctly.
#
# NOTE: In the following description, all the fields whose names start with
# BPB are part of the BPB. All the fields whose names start with BS_ are part
# of the boot sector and not really part of the BPB.
#
# =============================================================================
class BPB(sector.Sector, ABC):
    """
    The BPB (BIOS Parameter Block) is located in the first sector of the
    volume in the Reserve Region. This sector is sometimes called the “boot
    sector” or the “0th sector”. The important fact to note is that this
    sector is simply the first sector of the volume.

    All FAT volumes must have a BPB in the boot sector. The BPB has evolved
    over the years as follows:
        • The FAT implementation in MS-DOS 1.x did not include a BPB
          (introduced in MS-DOS 2.x)
        • The BPB in MS-DOS 3.x was modified to allow > 64K sectors
        • For FAT32, the BPB differs from that for FAT16/FAT12 beginning at
          offset 36.

    The BPB in the boot sector of a FAT volume must always have all of the
    BPB fields for either the FAT12/FAT16 or FAT32 BPB type. This ensures
    maximum compatibility of the FAT volume and will also ensure that all
    FAT file system drivers understand and support the volume correctly.
    """
    _NO_VOLLAB = "NO NAME"

    _MEDIA = [
        0xF0,
        0xF8,
        0xF9,
        0xFA,
        0xFB,
        0xFC,
        0xFD,
        0xFE,
        0xFF,
    ]

    _TYPE = {
        "FAT12": 0x00,
        "FAT16": 0x01,
        "FAT32": 0x02,
    }

    _SIGNATURE = 0xAA55

    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 sector_in: int = 0, size_in: int = int(0.5 * data.Data._KiB)):
        super().__init__(data_in, endianness_in, sector_in, size_in)
        # Set the shift value for the sector size
        self.__shift = int(math.log(size_in, 2))

    def format(self, bytes_per_sec_in: int = 512, media_in: int = 0xF8):
        # Update the size of this sector.
        self.size = bytes_per_sec_in

        # Set the shift value for the sector size
        self.__shift = int(math.log(bytes_per_sec_in, 2))

        # Count of bytes per sector. This value may take on only the following
        # values: 512, 1024, 2048 or 4096.
        self.BPB_BytsPerSec = bytes_per_sec_in

        # Number of sectors per allocation unit. This value must be a power of
        # 2 that is greater than 0. The legal values are 1, 2, 4, 8, 16, 32, 64,
        # and 128.
        self.BPB_SecPerClus = self.sec_per_cluster

        # Number of reserved sectors in the reserved region of the volume
        # starting at the first sector of the volume. This field is used to
        # align the start of the data area to integral multiples of the cluster
        # size with respect to the start of the partition/media. This field
        # must not be 0 and can be any non-zero value. This field should
        # typically be used to align the start of the data area (cluster #2)
        # to the desired alignment unit, typically cluster size.
        self.BPB_RsvdSecCnt = 1

        # The count of file allocation tables (FATs) on the volume. A value of
        # 2 is recommended although a value of 1 is acceptable.
        self.BPB_NumFATs = 2

        # For FAT12 and FAT16 volumes, this field contains the count of 32-byte
        # directory entries in the root directory. For FAT32 volumes, this field
        # must be set to 0. For FAT12 and FAT16 volumes, this value should always
        # specify a count that when multiplied by 32 results in an even multiple
        # of BPB_BytsPerSec.

        # For maximum compatibility, FAT16 volumes should use the value 512.
        self.BPB_RootEntCnt = 0

        # This field can be 0; if it is 0, then BPB_TotSec32 must be non-zero.
        # For FAT32 volumes, this field must be 0. This value shall be
        # overwritten by child tables at format.
        sectors = self.total_sectors
        if sectors > 0xFFFF:
            self.BPB_TotSec32 = sectors
        else:
            self.BPB_TotSec16 = sectors

        # 0xF8 is the standard value for “fixed” (nonremovable) media. For
        # removable media, 0xF0 is frequently used.
        self.BPB_Media = media_in

        # This field is the FAT12/FAT16 16-bit count of sectors occupied by one
        # FAT. On FAT32 volumes this field must be 0, and BPB_FATSz32 contains
        # the FAT size count.
        self.BPB_FATSz16 = 0

        # This field is only relevant for media that have a geometry (volume is
        # broken down into tracks by multiple heads and cylinders) and are
        # visible on interrupt 0x13.
        self.BPB_SecPerTrk = self.sectors_per_trak

        # To calculate the number of heads on a disk, divide the total storage
        # capacity by the product of cylinders, sectors per track, and bytes
        # per sector. Typically, each physical platter has two sides, equating
        # to two read/write heads per platter. Here we assume the average
        # number of platters.
        self.BPB_NumHeads = self.heads

    @property
    def BPB_BytsPerSec(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_BytsPerSec                    | 11                | 2             |
        -----------------------------------------------------------------------
        @brief Count of bytes per sector. This value may take on only the
        following values: 512, 1024, 2048 or 4096. If maximum compatibility
        with old implementations is desired, only the value 512 should be
        used. There is a lot of FAT code in the world that is basically
        “hard-wired” to 512 bytes per sector and doesn’t bother to check
        this field to make sure it is 512. Microsoft operating systems will
        properly support 1024, 2048, and 4096.

        @note: Do not misinterpret these statements about maximum
        compatibility. If the media being recorded has a physical sector
        size N, you must use N and this must still be less than or equal
        to 4096. Maximum compatibility is achieved by only using media
        with specific sector sizes.

        :return: int: Count of bytes per sector.
        """
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 11)[0]

    @BPB_BytsPerSec.setter
    def BPB_BytsPerSec(self, bytes_in: int):
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_BytsPerSec                    | 11                | 2             |
        -----------------------------------------------------------------------
        @brief Count of bytes per sector. This value may take on only the
        following values: 512, 1024, 2048 or 4096. If maximum compatibility
        with old implementations is desired, only the value 512 should be
        used. There is a lot of FAT code in the world that is basically
        “hard-wired” to 512 bytes per sector and doesn’t bother to check
        this field to make sure it is 512. Microsoft operating systems will
        properly support 1024, 2048, and 4096.

        @note: Do not misinterpret these statements about maximum
        compatibility. If the media being recorded has a physical sector
        size N, you must use N and this must still be less than or equal
        to 4096. Maximum compatibility is achieved by only using media
        with specific sector sizes.

        :param bytes_in: int: Count of bytes per sector. This value may take on
        only the following values: 512, 1024, 2048 or 4096.
        """

        # This value may take on only the following values: 512, 1024, 2048
        # or 4096. If the media being recorded has a physical sector size N,
        # you must use N and this must still be less than or equal to 4096.

        # The value shall be less than or equal to 4096.
        self._verify_size(bytes_in)
        struct.pack_into(
            f"{self.endianness}H",
            self.data,
            11,
            bytes_in)

    @property
    def BPB_SecPerClus(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_SecPerClus                    | 13                | 1             |
        -----------------------------------------------------------------------
        Number of sectors per allocation unit. This value must be a power
        of 2 that is greater than 0. The legal values are 1, 2, 4, 8, 16,
        32, 64, and 128. Note however, that a value should never be used
        that results in a “bytes per cluster” value (BPB_BytsPerSec *
        BPB_SecPerClus) greater than 32K (32 * 1024). There is a
        misconception that values greater than this are OK. Values that
        cause a cluster size greater than 32K bytes do not work properly;
        do not try to define one. Some versions of some systems allow 64K
        bytes per cluster value. Many application setup programs will not
        work correctly on such a FAT volume.

        :return: int: Number of sectors per allocation unit.
        """
        return struct.unpack_from(
            f"{self.endianness}B",
            self.data, 13)[0]

    @BPB_SecPerClus.setter
    def BPB_SecPerClus(self, sectors_in: int):
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_SecPerClus                    | 13                | 1             |
        -----------------------------------------------------------------------
        Number of sectors per allocation unit. This value must be a power
        of 2 that is greater than 0. The legal values are 1, 2, 4, 8, 16,
        32, 64, and 128. Note however, that a value should never be used
        that results in a “bytes per cluster” value (BPB_BytsPerSec *
        BPB_SecPerClus) greater than 32K (32 * 1024). There is a
        misconception that values greater than this are OK. Values that
        cause a cluster size greater than 32K bytes do not work properly;
        do not try to define one. Some versions of some systems allow 64K
        bytes per cluster value. Many application setup programs will not
        work correctly on such a FAT volume.

        :param sectors_in: int: Number of sectors per allocation unit. This
        value must be a power of 2 that is greater than 0
        """

        # A power of 2 has exactly one bit set to 1 in its binary
        # representation (e.g., is 1000). Subtracting 1 flips all bits after
        # that 1 to 1 and the leading 1 to 0 (e.g., is 0111). Performing a
        # bitwise & on these two values will always result in zero for powers
        # of 2.
        if ((sectors_in - 1) & sectors_in) == 0 and sectors_in > 0:
            struct.pack_into(
                f"{self.endianness}B",
                self.data,
                13,
                sectors_in)
        else:
            raise ValueError(
                f"Warning: BPB_SecPerClus: {sectors_in}\n"
                f"This value must be a power of 2 that is greater than 0.")

    @property
    def BPB_RsvdSecCnt(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_RsvdSecCnt                    | 14                | 2             |
        -----------------------------------------------------------------------
        Number of reserved sectors in the Reserved region of the volume
        starting at the first sector of the volume. This field must not be
        0. For FAT12 and FAT16 volumes, this value should never be
        anything other than 1. For FAT32 volumes, this value is typically
        32. There is a lot of FAT code in the world “hard-wired” to 1
        reserved sector for FAT12 and FAT16 volumes and that doesn’t
        bother to check this field to make sure it is 1. Microsoft
        operating systems will properly support any non-zero value in this
        field.

        :return: int: Number of reserved sectors in the Reserved region of
        the volume starting at the first sector of the volume.
        """
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 14)[0]

    @BPB_RsvdSecCnt.setter
    def BPB_RsvdSecCnt(self, count_in: int):
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_RsvdSecCnt                    | 14                | 2             |
        -----------------------------------------------------------------------
        Number of reserved sectors in the Reserved region of the volume
        starting at the first sector of the volume. This field must not be 0.
        For FAT12 and FAT16 volumes, this value should never be anything other
        than 1. For FAT32 volumes, this value is typically 32. There is a lot
        of FAT code in the world “hard-wired” to 1 reserved sector for FAT12
        and FAT16 volumes and that doesn’t bother to check this field to make
        sure it is 1. Microsoft operating systems will properly support any
        non-zero value in this field.

        :param count_in: int: Number of reserved sectors in the Reserved region
        of the volume starting at the first sector of the volume.
        """

        # This field must not be 0. For FAT12 and FAT16 volumes, this value
        # should never be anything other than 1. For FAT32 volumes, this value
        # is typically 32.
        if count_in > 0:
            struct.pack_into(
                f"{self.endianness}H", self.data,
                14, count_in)
        else:
            raise ValueError(
                f"Error: BPB_RsvdSecCnt: {count_in}\n"
                f"This field must not be 0.")

    @property
    def BPB_NumFATs(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_NumFATs                        | 16               | 1             |
        -----------------------------------------------------------------------
        The count of FAT data structures on the volume. This field should
        always contain the value 2 for any FAT volume of any type.
        Although any value greater than or equal to 1 is perfectly valid,
        many software programs and a few operating systems’ FAT file
        system drivers may not function properly if the value is something
        other than 2. All Microsoft file system drivers will support a
        value other than 2, but it is still highly recommended that no
        value other than 2 be used in this field.
        The reason the standard value for this field is 2 is to provide
        redundancy for the FAT data structure so that if a sector goes
        bad in one of the FATs, that data is not lost because it is
        duplicated in the other FAT. On non-disk-based media, such as
        FLASH memory cards, where such redundancy is a useless feature, a
        value of 1 may be used to save the space that a second copy of the
        FAT uses, but some FAT file system drivers might not recognize such
        a volume properly.

        :return: int: The count of FAT data structures on the volume.
        """
        return struct.unpack_from(
            f"{self.endianness}B",
            self.data, 16)[0]

    @BPB_NumFATs.setter
    def BPB_NumFATs(self, number_in: int):
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_NumFATs                        | 16                | 1            |
        -----------------------------------------------------------------------
        The count of FAT data structures on the volume. This field should
        always contain the value 2 for any FAT volume of any type.
        Although any value greater than or equal to 1 is perfectly valid,
        many software programs and a few operating systems’ FAT file
        system drivers may not function properly if the value is something
        other than 2. All Microsoft file system drivers will support a
        value other than 2, but it is still highly recommended that no
        value other than 2 be used in this field.
        The reason the standard value for this field is 2 is to provide
        redundancy for the FAT data structure so that if a sector goes
        bad in one of the FATs, that data is not lost because it is
        duplicated in the other FAT. On non-disk-based media, such as
        FLASH memory cards, where such redundancy is a useless feature, a
        value of 1 may be used to save the space that a second copy of the
        FAT uses, but some FAT file system drivers might not recognize such
        a volume properly.

        :param number_in: int: The count of FAT data structures on the volume.
        """

        # Any value greater than or equal to 1 is perfectly valid, many software
        # programs and a few operating systems’ FAT file system drivers may not
        # function properly if the value is something other than 2.
        if number_in >= 1:
            struct.pack_into(
                f"{self.endianness}B", self.data,
                16, number_in)
        else:
            raise ValueError(
                f"Error: Invalid BPB_NumFATs: {number_in}\n"
                f"Value must be greater than or equal to 1.")

    @property
    def BPB_RootEntCnt(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_RootEntCnt                    | 17                | 2             |
        -----------------------------------------------------------------------
        For FAT12 and FAT16 volumes, this field contains the count of 32-
        byte directory entries in the root directory. For FAT32 volumes,
        this field must be set to 0. For FAT12 and FAT16 volumes, this
        value should always specify a count that when multiplied by 32
        results in an even multiple of BPB_BytsPerSec. For maximum
        compatibility, FAT16 volumes should use the value 512.

        :return: int: The count of 32-byte directory entries in the root
        directory.
        """
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 17)[0]

    @BPB_RootEntCnt.setter
    def BPB_RootEntCnt(self, entry_count_in: int):
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_RootEntCnt                    | 17                | 2             |
        -----------------------------------------------------------------------
        For FAT12 and FAT16 volumes, this field contains the count of 32-byte
        directory entries in the root directory. For FAT32 volumes, this field
        must be set to 0. For FAT12 and FAT16 volumes, this value should always
        specify a count that when multiplied by 32 results in an even multiple
        of BPB_BytsPerSec. For maximum compatibility, FAT16 volumes should use
        the value 512.

        :param entry_count_in: int: The count of 32-byte directory entries
        in the root directory.
        """
        struct.pack_into(
            f"{self.endianness}H", self.data,
            17, entry_count_in)

    @property
    def BPB_TotSec16(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_TotSec16                       | 19               | 2             |
        -----------------------------------------------------------------------
        This field is the old 16-bit total count of sectors on the volume.
        This count includes the count of all sectors in all four regions of the
        volume. This field can be 0; if it is 0, then BPB_TotSec32 must be
        non-zero. For FAT32 volumes, this field must be 0. For FAT12 and
        FAT16 volumes, this field contains the sector count, and
        BPB_TotSec32 is 0 if the total sector count “fits” (is less than
        0x10000).

        :return: int: The old 16-bit total count of sectors on the volume.
        """
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 19)[0]

    @BPB_TotSec16.setter
    def BPB_TotSec16(self, sectors_in: int):
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_TotSec16                       | 19               | 2             |
        -----------------------------------------------------------------------
        This field is the old 16-bit total count of sectors on the volume.
        This count includes the count of all sectors in all four regions of the
        volume. This field can be 0; if it is 0, then BPB_TotSec32 must be
        non-zero. For FAT32 volumes, this field must be 0. For FAT12 and
        FAT16 volumes, this field contains the sector count, and
        BPB_TotSec32 is 0 if the total sector count “fits” (is less than
        0x10000).

        :param sectors_in: int: The old 16-bit total count of sectors on the
        volume.
        """

        # For FAT12 and FAT16 volumes, this field contains the sector count,
        # and BPB_TotSec32 is 0 if the total sector count “fits” (is less than
        # 0x10000).
        if sectors_in < 0x10000:
            struct.pack_into(
                f"{self.endianness}H", self.data,
                19, sectors_in)
        else:
            raise ValueError(
                f"Error: Invalid BPB_TotSec16: {sectors_in}\n"
                f"Value must be less than 0x10000")

    @property
    def BPB_Media(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_Media                          | 21               | 1             |
        -----------------------------------------------------------------------
        0xF8 is the standard value for “fixed” (non-removable) media. For
        removable media, 0xF0 is frequently used. The legal values for this
        field are 0xF0, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, and
        0xFF. The only other important point is that whatever value is put
        in here must also be put in the low byte of the FAT[0] entry. This
        dates back to the old MS-DOS 1.x media determination noted
        earlier and is no longer usually used for anything.

        :return: int: The storage medium type (e.g., hard disk or removable
        floppy)
        """
        return struct.unpack_from(
            f"{self.endianness}B",
            self.data, 21)[0]

    @BPB_Media.setter
    def BPB_Media(self, type_in: int):
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_Media                          | 21               | 1             |
        -----------------------------------------------------------------------
        0xF8 is the standard value for “fixed” (non-removable) media. For
        removable media, 0xF0 is frequently used. The legal values for this
        field are 0xF0, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, and
        0xFF. The only other important point is that whatever value is put
        in here must also be put in the low byte of the FAT[0] entry. This
        dates back to the old MS-DOS 1.x media determination noted
        earlier and is no longer usually used for anything.

        :param type_in: int: The storage medium type (e.g., hard disk or
        removable floppy)
        """
        if type_in in self._MEDIA:
            struct.pack_into(
                f"{self.endianness}B", self.data,
                21, type_in)
        else:
            raise ValueError(
                f"Error: Invalid BPB_Media: {type_in}\n"
                f"Valid Values: {self._MEDIA}")

    @property
    def BPB_FATSz16(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_FATSz16                        | 22               | 2             |
        -----------------------------------------------------------------------
        This field is the FAT12/FAT16 16-bit count of sectors occupied by
        ONE FAT. On FAT32 volumes this field must be 0, and
        BPB_FATSz32 contains the FAT size count.

        :return: int: The FAT12/FAT16 16-bit count of sectors occupied by
        ONE FAT. On FAT32, 0. The count is found in the BPB_FATSz32.
        """
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 22)[0]

    @BPB_FATSz16.setter
    def BPB_FATSz16(self, size_in: int):
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_FATSz16                        | 22               | 2            |
        -----------------------------------------------------------------------
        This field is the FAT12/FAT16 16-bit count of sectors occupied by
        ONE FAT. On FAT32 volumes this field must be 0, and
        BPB_FATSz32 contains the FAT size count.

        :return: int: The FAT12/FAT16 16-bit count of sectors occupied by
        ONE FAT. On FAT32, 0. The count is found in the BPB_FATSz32.
        """
        if size_in > 0:
            self.BPB_FATSz32 = 0

        struct.pack_into(
            f"{self.endianness}H", self.data,
            22, size_in)

    @property
    def BPB_SecPerTrk(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_SecPerTrk                      | 24               | 2             |
        -----------------------------------------------------------------------
        Sectors per track for interrupt 0x13. This field is only relevant
        for media that have a geometry (volume is broken down into tracks
        by multiple heads and cylinders) and are visible on interrupt 0x13.
        This field contains the “sectors per track” geometry value.

        :return: int: Sectors per track for interrupt 0x13.
        """
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 24)[0]

    @BPB_SecPerTrk.setter
    def BPB_SecPerTrk(self, sectors_in: int):
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_SecPerTrk                      | 24               | 2             |
        -----------------------------------------------------------------------
        Sectors per track for interrupt 0x13. This field is only relevant
        for media that have a geometry (volume is broken down into tracks
        by multiple heads and cylinders) and are visible on interrupt 0x13.
        This field contains the “sectors per track” geometry value.

        :return: int: Sectors per track for interrupt 0x13.
        """
        struct.pack_into(
            f"{self.endianness}H", self.data,
            24, sectors_in)

    @property
    def BPB_NumHeads(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_NumHeads                       | 26               | 2             |
        -----------------------------------------------------------------------
        Number of heads for interrupt 0x13. This field is relevant as
        discussed earlier for BPB_SecPerTrk. This field contains the one
        based “count of heads”. For example, on a 1.44 MB 3.5-inch floppy
        drive this value is 2.

        :return: int: Number of heads for interrupt 0x13.
        """
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 26)[0]

    @BPB_NumHeads.setter
    def BPB_NumHeads(self, heads_in: int):
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_NumHeads                       | 26               | 2             |
        -----------------------------------------------------------------------
        Number of heads for interrupt 0x13. This field is relevant as
        discussed earlier for BPB_SecPerTrk. This field contains the one
        based “count of heads”. For example, on a 1.44 MB 3.5-inch floppy
        drive this value is 2.

        :return: int: Number of heads for interrupt 0x13.
        """
        struct.pack_into(
            f"{self.endianness}H", self.data,
            26, heads_in)

    @property
    def BPB_HiddSec(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_HiddSec                        | 28               | 4            |
        -----------------------------------------------------------------------
        Count of hidden sectors preceding the partition that contains this
        FAT volume. This field is generally only relevant for media visible
        on interrupt 0x13. This field should always be zero on media that
        are not partitioned. Exactly what value is appropriate is operating
        system specific.

        :return: int:  Count of hidden sectors preceding the partition that
        contains this FAT volume.
        """
        return struct.unpack_from(
            f"{self.endianness}L",
            self.data, 28)[0]

    @property
    def BPB_TotSec32(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_TotSec32                       | 32               | 4             |
        -----------------------------------------------------------------------
        This field is the new 32-bit total count of sectors on the volume.
        This count includes the count of all sectors in all four regions of
        the volume. This field can be 0; if it is 0, then BPB_TotSec16 must
        be non-zero. For FAT32 volumes, this field must be non-zero. For
        FAT12/FAT16 volumes, this field contains the sector count if
        BPB_TotSec16 is 0 (count is greater than or equal to 0x10000).

        :return: int: The new 32-bit total count of sectors on the volume.
        """
        return struct.unpack_from(
            f"{self.endianness}L",
            self.data,32)[0]

    @BPB_TotSec32.setter
    def BPB_TotSec32(self, sectors_in: int):
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        BPB_TotSec32                       | 32               | 4             |
        -----------------------------------------------------------------------
        This field is the new 32-bit total count of sectors on the volume.
        This count includes the count of all sectors in all four regions of
        the volume. This field can be 0; if it is 0, then BPB_TotSec16 must
        be non-zero. For FAT32 volumes, this field must be non-zero. For
        FAT12/FAT16 volumes, this field contains the sector count if
        BPB_TotSec16 is 0 (count is greater than or equal to 0x10000).

        :param sectors_in: int: The new 32-bit total count of sectors on the
        volume.
        """

        # Only one of the two values: BPB_TotSec16 or BPB_TotSec32 shall be
        # set.
        if sectors_in > 0:
            self.BPB_TotSec16 = 0

        struct.pack_into(
            f"{self.endianness}L", self.data,
            32, sectors_in)

    @property
    def Signature_word(self) -> int:
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        Signature_word                     | 510              | 2             |
        -----------------------------------------------------------------------
        Set to 0x55 (at byte offset 510) and 0xAA (at byte offset 511)

        :return: int: 0xAA55
        """
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 510)[0]

    @Signature_word.setter
    def Signature_word(self, signature_in: int):
        """
        Name                              | Offset (Byte)     | Size (Bytes)  |
        -----------------------------------------------------------------------
        Signature_word                     | 510              | 2             |
        -----------------------------------------------------------------------
        Set to 0x55 (at byte offset 510) and 0xAA (at byte offset 511)

        :param signature_in: int: 0xAA55
        """
        struct.pack_into(
            f"{self.endianness}H", self.data,
            510, signature_in)

    @property
    @abstractmethod
    def BS_FilSysType(self) -> str:
        return ""

    @property
    def type(self) -> int:
        """
        To determine the FAT type (FAT12, FAT16, or FAT32) from a disk, analyze
        the BIOS Parameter Block (BPB) in the boot sector (first sector). The
        crucial indicator is the total number of clusters: < 4086 is FAT12,
        4086-65525 is FAT16, and > 65526 is FAT32.
        """
        if self.data_clusters < 4086:
            return self._TYPE["FAT12"]
        elif self.data_clusters < 65526:
            return self._TYPE["FAT16"]
        else:
            return self._TYPE["FAT32"]

    @property
    def valid(self) -> bool:
        return self.Signature_word == 0xAA55

    @property
    def root_sector(self) -> int:
        return (((self.BPB_RootClus - 2) * self.BPB_BytsPerSec) +
                self.data_sector)

    @property
    def root_sectors(self) -> int:
        # Note that on a FAT32 volume, the BPB_RootEntCnt value is always 0.
        # Therefore, on a FAT32 volume, RootDirSectors is always 0.
        return math.ceil(((self.BPB_RootEntCnt * directory.Directory.LENGTH) +
                (self.BPB_BytsPerSec - 1)) / self.BPB_BytsPerSec)

    @property
    def root_offset(self) -> int:
        return self.root_sector * self.BPB_BytsPerSec

    @property
    def data_sector(self) -> int:
        return (self.BPB_RsvdSecCnt + self.root_sectors +
                self.BPB_FATSz16 * self.BPB_NumFATs)

    @property
    def data_sectors(self) -> int:
        return self.total_sectors - self.data_sector

    @property
    def data_offset(self) -> int:
        return self.data_sector * self.BPB_BytsPerSec

    @property
    def data_clusters(self) -> int:
        # Add 2 for the two reserved entries in the FAT
        return ((self.total_sectors - self.data_sector) //
                self.sec_per_cluster) + 2

    @property
    def sec_per_cluster(self) -> int:
        sectors = (self.disk_size & 0xFFFFFFFFFFFFC00) >> self.__shift
        TWOMiB = 1 << 21
        TWOKiB = 1 << 11
        return 64 if sectors > 32 * TWOMiB else (
            32 if sectors > 16 * TWOMiB else (
                16 if sectors >  8 * TWOMiB else (
                    8 if sectors > 260 * TWOKiB else 1)))

    @property
    def heads(self) -> int:
        sectors = (self.disk_size & 0xFFFFFFFFFFFFC00) >> self.__shift
        SIXTYTHREEKiB = 0xFC00
        if sectors <= 0X80000:
            # For capacity below the 256MB (with 512b sectors) use CHS
            # Recommendation from SD Card Part 2 File System Specification
            return 2 if sectors <= (1 << 15) else (
                4 if sectors <=  (1 << 16) else (
                    8 if sectors <= (1 << 18) else
                    16))
        else:
            # Use LBA-Assist Translation for calculating CHS when disk geometry
            # is not available
            return 16 if sectors <= 16 * SIXTYTHREEKiB else (
                32 if sectors <= 32 * SIXTYTHREEKiB else (
                    64 if sectors <= 64 * SIXTYTHREEKiB else (
                        128 if sectors <= 128 * SIXTYTHREEKiB else
                        255)))

    @property
    def sectors_per_trak(self) -> int:
        sectors = (self.disk_size & 0xFFFFFFFFFFFFC00) >> self.__shift
        if sectors <= 524288:
            return 16 if sectors_in <= 0x1000 else 32
        else:
            return 63

    @property
    def total_sectors(self) -> int:
        sectors = (self.disk_size & 0xFFFFFFFFFFFFC00) >> self.__shift
        if sectors <= 0xFFFFFFFF:
            # Align number of sectors to be multiple of sectors per track,
            # needed by DOS and mtools
            return (sectors // self.sectors_per_trak) * self.sectors_per_trak
        else:
            return 0xFFFFFFFF

    @property
    def BPB_FFATSz(self) -> int:
        return self.BPB_FATSz16

    def _compute_fat_size(self, entry_size_in: float) -> int:
        free = self.total_sectors - self.BPB_RsvdSecCnt - self.root_sectors
        for size in range(self.total_sectors):
            # Next, determine the count of sectors in the data region of the volume:
            data_sectors = free - (self.BPB_NumFATs * size)

            # The FAT (File Allocation Table) must contain entries, where
            # is the total number of data clusters available for storing
            # files and directories.
            clusters = int(data_sectors / self.BPB_SecPerClus) + 2

            # The required size for fit entries for all data clusters
            required = math.ceil(clusters * entry_size_in)

            # Actual size of the FAT.
            actual = (size * self.BPB_BytsPerSec)

            # If it fits... we must acquit
            if required <= actual:
                return size





