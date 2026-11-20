#!/usr/bin/env python3
import struct, os, re
import data, timestamp, fat


# =============================================================================
# Directory Structure
# -----------------------------------------------------------------------------
# A FAT directory is a special file type. The directory serves as a container
# for other files and subdirectories. Directory contents (data) are a series
# of 32 byte directory entries. Each directory entry in turn, typically
# represents a contained file or sub-directory directory.
#
# =============================================================================
class Directory(data.Data):
    """
    A FAT directory is a special file type. The directory serves as a
    container for other files and subdirectories. Directory contents
    (data) are a series of 32 byte directory entries. Each directory
    entry in turn, typically represents a contained file or subdirectory
    directory.
    """
    LENGTH = 0x00000020

    # The maximum file size is 0xFFFFFFFF bytes. Any chain of clusters
    # allocated to a file must be <= 0x100000000 bytes. The last byte in
    # such a chain of clusters cannot be part of the file.
    MAX_FILE = 0xFFFFFFFF

    # The maximum valid directory size is 2^21 bytes.
    MAX_DIR  = 0x3FFFFF

    # Legal file attribute types are as defined below:
    # ---------------------------------------------------
    # Name                          | Value             |
    # ---------------------------------------------------
    # ATTR_READ_ONLY                | 0x01              |
    # ATTR_HIDDEN                   | 0x02              |
    # ATTR_SYSTEM                   | 0x04              |
    # ATTR_VOLUME_ID                | 0x08              |
    # ATTR_DIRECTORY                | 0x10              |
    # ATTR_ARCHIVE                  | 0x20              |
    # ATTR_LONG_NAME                | ATTR_READ_ONLY |  |
    #                               | ATTR_HIDDEN |     |
    #                               | ATTR_SYSTEM |     |
    #                               | ATTR_VOLUME_ID    |
    # ---------------------------------------------------
    # The upper two bits of the attribute byte are reserved and must always
    # be set to 0 when a file is created. These bits are not interpreted.

    # The file cannot be modified – all modification requests must fail with an
    # appropriate error code value.
    ATTR_READ_ONLY = 0x01

    # The corresponding file or subdirectory must not be listed unless a
    # request is issued by the user/application explicitly requesting inclusion
    # of “hidden files”
    ATTR_HIDDEN = 0x02

    # The corresponding file is tagged as a component of the operating system.
    # It must not be listed unless a request is issued by the user/application
    # explicitly requesting inclusion of “system files”.
    ATTR_SYSTEM = 0x04

    # The corresponding entry contains the volume label. DIR_FstClusHI and
    # DIR_FstClusLO must always be 0 for the corresponding entry (representing
    # the volume label) since no clusters can be allocated for this entry. Only
    # the root directory (see Section 6.x below) can contain one entry with
    # this attribute. No subdirectory must contain an entry of this type.
    # Entries representing long file names (see Section 7) are exceptions to
    # these rules.
    ATTR_VOLUME_ID = 0x08

    # The corresponding entry represents a directory (a child or subdirectory
    # to the containing directory). DIR_FileSize for the corresponding entry
    # must always be 0 (even though clusters may have been allocated for the
    # directory).
    ATTR_DIRECTORY = 0x10

    # This attribute must be set when the file iscreated, renamed, or modified.
    # The presence of this attribute indicates that properties of the
    # associated file have been modified. Backup utilities can utilize this
    # information to determine the set of files that need to be backed up to
    # ensure protection in case of media and other failure conditions.
    ATTR_ARCHIVE = 0x20

    ATTR_LONG_NAME = ATTR_READ_ONLY | ATTR_HIDDEN | ATTR_SYSTEM | ATTR_VOLUME_ID

    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 fat_in: fat.FAT, data_offset_in: int, offset_in: int = 0x00000000,
                 size_in: int = 0, name_in: str = "", attributes_in: int = 0x0):
        super().__init__(data_in, endianness_in, offset_in, self.LENGTH)
        self.__fat = fat_in
        self.__data_offset = data_offset_in

        self.DIR_FileSize = size_in
        self.DIR_Name = name_in
        self.DIR_Attr = attributes_in

        # Set DIR_NTRes to 0.
        # Set DIR_NTRes to 0.
        struct.pack_into(
            f"{self.endianness}B",
            self.data, 12, 0x0000)

        # Root Directory
        # The root directory is a special container file created during volume
        # initialization (format) and,therefore, always present on the
        # formatted volume.
        # Only the root directory can contain an entry with the DIR_Attr field
        # contents equal to ATTR_VOLUME_ID.
        if attributes_in & self.ATTR_VOLUME_ID:
            # There is no name for the root directory (on most operating system
            # implementations, the implied name “\” is used). Further, the root
            # directory does not have any associated date/time stamps. Lastly,
            # the root directory does not contain either the dot or dotdot
            # entries.
            self.DIR_FileSize = 0
            self.DIR_Name = ""
            self.DIR_FstClus = self.__fat.allocate()

        else:
            # Leave the data as-is for investigation
            pass

    @property
    def free(self) -> bool:
        return (not self.DIR_Attr & self.ATTR_VOLUME_ID and (
                # DIR_Name[0] = 0xE5 indicates the directory entry is free
                # (available). However, 0xE5 is a valid KANJI lead byte value
                # for the character set used in Japan. For KANJI character set
                # based names, the value 0x05 is stored in DIR_Name[0] - if
                # required - to represent 0xE5.
                # If the FAT file system implementation reads DIR_NAME[0] =
                # 0x05 and if the character set used is KANJI, it must perform
                # the appropriate substitution in memory prior to returning the
                # name to the application.
                self.data[0] == 0xE5 or
                # DIR_Name[0] = 0x00 also indicates the directory entry is free
                # (available). However, DIR_Name[0] = 0x00 is an additional
                # indicator that all directory entries following the current
                # free entry are also free.
                self.data[0] == 0x00))

    @free.setter
    def free(self, free_in: bool):
        # DIR_Name[0] = 0xE5 indicates the directory entry is free
        # (available). However, 0xE5 is a valid KANJI lead byte value for the
        # character set used in Japan. For KANJI character set based names, the
        # value 0x05 is stored in DIR_Name[0] - if required - to represent 0xE5.
        # If the FAT file system implementation reads DIR_NAME[0] = 0x05 and if
        # the character set used is KANJI, it must perform the appropriate
        # substitution in memory prior to returning the name to the
        # application.
        struct.pack_into(
            f"{self.endianness}B", self.data,
            0, 0xE5)

    @property
    def DIR_Name(self) -> str:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_Name         | 0                | 11            |
        ------------------------------------------------------
        “Short” file name limited to 11 characters (8.3 format).

        :return: str: “Short” file name.
        """
        name = struct.unpack_from(
            f"{self.endianness}8s",
            self.data, 0)[0].rstrip(b"\x00").decode('ascii')
        ext = struct.unpack_from(
            f"{self.endianness}3s",
            self.data, 8)[0].rstrip(b"\x00").decode('ascii')
        return f"{name}{(f".{ext}" if ext != "" else "")}"

    @DIR_Name.setter
    def DIR_Name(self, name_in: str):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_Name         | 0                | 11            |
        ------------------------------------------------------
        “Short” file name limited to 11 characters (8.3 format).

        :param name_in: str: “Short” file name.
        """
        name, ext = os.path.splitext(name_in.upper())

        # The 8-character main part of the name
        struct.pack_into(
            f"{self.endianness}8s", self.data,
            0, f"{name[:8]}".encode("ascii"))

        # The 3-character extension
        struct.pack_into(
            f"{self.endianness}3s", self.data,
            8, f"{ext[:3]}".encode("ascii"))

    @property
    def DIR_Attr(self) -> int:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_StrucSig      | 11               | 1             |
        ------------------------------------------------------

        Legal file attribute types are as defined below:
        ---------------------------------------------------
        Name                          | Value             |
        ---------------------------------------------------
        ATTR_READ_ONLY                | 0x01              |
        ATTR_HIDDEN                   | 0x02              |
        ATTR_SYSTEM                   | 0x04              |
        ATTR_VOLUME_ID                | 0x08              |
        ATTR_DIRECTORY                | 0x10              |
        ATTR_ARCHIVE                  | 0x20              |
        ATTR_LONG_NAME                | ATTR_READ_ONLY |  |
                                      | ATTR_HIDDEN |     |
                                      | ATTR_SYSTEM |     |
                                      | ATTR_VOLUME_ID    |
        ---------------------------------------------------
        The upper two bits of the attribute byte are reserved and must always
        be set to 0 when a file is created. These bits are not interpreted.

        :return: int: File attribute flags.
        """
        return struct.unpack_from(
            f"{self.endianness}B",
            self.data, 11)[0]

    @DIR_Attr.setter
    def DIR_Attr(self, attributes_in: int):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        FSI_StrucSig      | 11               | 1             |
        ------------------------------------------------------

        Legal file attribute types are as defined below:
        ---------------------------------------------------
        Name                          | Value             |
        ---------------------------------------------------
        ATTR_READ_ONLY                | 0x01              |
        ATTR_HIDDEN                   | 0x02              |
        ATTR_SYSTEM                   | 0x04              |
        ATTR_VOLUME_ID                | 0x08              |
        ATTR_DIRECTORY                | 0x10              |
        ATTR_ARCHIVE                  | 0x20              |
        ATTR_LONG_NAME                | ATTR_READ_ONLY |  |
                                      | ATTR_HIDDEN |     |
                                      | ATTR_SYSTEM |     |
                                      | ATTR_VOLUME_ID    |
        ---------------------------------------------------
        The upper two bits of the attribute byte are reserved and must always
        be set to 0 when a file is created. These bits are not interpreted.

        :return: int: File attribute flags.
        """
        struct.pack_into(
            f"{self.endianness}B",
            self.data, 11, attributes_in)

    @property
    def DIR_NTRes(self) -> int:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_NTRes         | 12               | 1             |
        ------------------------------------------------------
        Reserved. Must be set to 0.

        :return: int: Shall be 0x00.
        """
        return struct.unpack_from(
            f"{self.endianness}B",
            self.data, 12)[0]

    @property
    def DIR_CrtTimeTenth(self) -> timestamp.Timestamp:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_CrtTimeTenth  | 13               | 1             |
        ------------------------------------------------------
        Component of the file creation time. Count of tenths of a second. Valid
        range is:
        0 <= DIR_CrtTimeTenth <= 199

        :return: int: Count of tenths of a second.
        """
        return timestamp.Timestamp(tenths_in=struct.unpack_from(
            f"{self.endianness}B",
            self.data, 13)[0])

    @DIR_CrtTimeTenth.setter
    def DIR_CrtTimeTenth(self, tenths_in: int | timestamp.Timestamp):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_CrtTimeTenth  | 13               | 1             |
        ------------------------------------------------------
        Component of the file creation time. Count of tenths of a second. Valid
        range is:
        0 <= DIR_CrtTimeTenth <= 199

        :param tenths_in: int: Count of tenths of a second.
        """
        struct.pack_into(
            f"{self.endianness}B", self.data,13,
            tenths_in.tenths if isinstance(tenths_in,
                    timestamp.Timestamp) else tenths_in)

    @property
    def DIR_CrtTime(self) -> timestamp.Timestamp:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_CrtTime      | 14              | 2             |
        ------------------------------------------------------
        Creation time. Granularity is 2 seconds.

        Directory entry timestamps are 16-bit values with a granularity of 2
        seconds. Contents of the DIR_CrtTime and DIR_WrtTime must be in the
        following format:
          - 0:4 contain elapsed seconds – as a count of 2-second increments
            (valid range: 0..29 inclusive allowing representation of 0 through
            58 seconds)
          - 5:10 represent number of minutes (valid range: 0..59 inclusive)
          - 11:15 represent hours (valid range: 0..23 inclusive)
        The valid time range is from Midnight 00:00:00 to 23:59:58.

        :return: int: Creation time.
        """
        return timestamp.Timestamp(date_in=struct.unpack_from(
            f"{self.endianness}H",
            self.data, 14)[0])

    @DIR_CrtTime.setter
    def DIR_CrtTime(self, time_in: int | timestamp.Timestamp):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_CrtTime      | 14              | 2             |
        ------------------------------------------------------
        Creation time. Granularity is 2 seconds.

        Directory entry timestamps are 16-bit values with a granularity of 2
        seconds. Contents of the DIR_CrtTime and DIR_WrtTime must be in the
        following format:
          - 0:4 contain elapsed seconds – as a count of 2-second increments
            (valid range: 0..29 inclusive allowing representation of 0 through
            58 seconds)
          - 5:10 represent number of minutes (valid range: 0..59 inclusive)
          - 11:15 represent hours (valid range: 0..23 inclusive)
        The valid time range is from Midnight 00:00:00 to 23:59:58.

        :param time_in: int: Creation time.
        """
        struct.pack_into(
            f"{self.endianness}H", self.data, 14,
            time_in.time if isinstance(time_in,
                    timestamp.Timestamp) else time_in)

    @property
    def DIR_CrtDate(self) -> timestamp.Timestamp:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_CrtDate       | 16               | 2             |
        ------------------------------------------------------
        Contents of the DIR_CrtDate, DIR_LstAccDate, and DIR_WrtDate fields
        must be in the following format:
          - 0:4 represent the day of the month (valid range: 1..31 inclusive)
          - 5:8 represent the month of the year (1 = January, 12 = December,
            valid range: 1..12 inclusive)
          - 9:15 are the count of years from 1980 (valid range: 0..127
            inclusive allowing representation of years 1980 through 2107)

        :return: int: Creation date.
        """
        return timestamp.Timestamp(date_in=struct.unpack_from(
            f"{self.endianness}H",
            self.data, 16)[0])

    @DIR_CrtDate.setter
    def DIR_CrtDate(self, date_in: int | timestamp.Timestamp):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_CrtDate       | 16               | 2             |
        ------------------------------------------------------
        Contents of the DIR_CrtDate, DIR_LstAccDate, and DIR_WrtDate fields
        must be in the following format:
          - 0:4 represent the day of the month (valid range: 1..31 inclusive)
          - 5:8 represent the month of the year (1 = January, 12 = December,
            valid range: 1..12 inclusive)
          - 9:15 are the count of years from 1980 (valid range: 0..127
            inclusive allowing representation of years 1980 through 2107)

        :return: int: Creation date.
        """
        struct.pack_into(
            f"{self.endianness}H", self.data,16,
            date_in.date if isinstance(date_in,
                    timestamp.Timestamp) else date_in)

    @property
    def DIR_LstAccDate(self) -> timestamp.Timestamp:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_LstAccDate    | 18               | 2             |
        ------------------------------------------------------
        Last access date. Last access is defined as a read or write operation
        performed on the file/directory described by this entry. This field
        must be updated on file modification (write operation) and the date
        value must be equal to DIR_WrtDate.

        Contents of the DIR_CrtDate, DIR_LstAccDate, and DIR_WrtDate fields
        must be in the following format:
          - 0:4 represent the day of the month (valid range: 1..31 inclusive)
          - 5:8 represent the month of the year (1 = January, 12 = December,
            valid range: 1..12 inclusive)
          - 9:15 are the count of years from 1980 (valid range: 0..127
            inclusive allowing representation of years 1980 through 2107)

        :return: int: Last access date.
        """
        return timestamp.Timestamp(date_in=struct.unpack_from(
            f"{self.endianness}H",
            self.data, 18)[0])


    @DIR_LstAccDate.setter
    def DIR_LstAccDate(self, date_in: int | timestamp.Timestamp):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_LstAccDate    | 18               | 2             |
        ------------------------------------------------------
        Last access date. Last access is defined as a read or write operation
        performed on the file/directory described by this entry. This field
        must be updated on file modification (write operation) and the date
        value must be equal to DIR_WrtDate.

        Contents of the DIR_CrtDate, DIR_LstAccDate, and DIR_WrtDate fields
        must be in the following format:
          - 0:4 represent the day of the month (valid range: 1..31 inclusive)
          - 5:8 represent the month of the year (1 = January, 12 = December,
            valid range: 1..12 inclusive)
          - 9:15 are the count of years from 1980 (valid range: 0..127
            inclusive allowing representation of years 1980 through 2107)

        :param date_in: int: Last access date.
        """
        struct.pack_into(
            f"{self.endianness}H", self.data,18,
            date_in.date if isinstance(date_in,
                    timestamp.Timestamp) else date_in)

    @property
    def DIR_FstClus(self) -> int:
        return ((self.DIR_FstClusHI & 0xFFFF) << 16) | (self.DIR_FstClusLO & 0xFFFF)

    @DIR_FstClus.setter
    def DIR_FstClus(self, cluster_in: int):
        self.DIR_FstClusHI = (cluster_in >> 16) & 0xFFFF
        self.DIR_FstClusLO = cluster_in & 0xFFFF

    @property
    def DIR_FstClusHI(self) -> int:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_FstClusHI     | 20               | 2             |
        ------------------------------------------------------
        High word of first data cluster number for file/directory described
        by this entry. Only valid for volumes formatted FAT32. Must be set to
        0 on volumes formatted FAT12/FAT16.

        :return: int: High word of first data cluster number for file/directory
        described by this entry.
        """
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 20)[0]

    @DIR_FstClusHI.setter
    def DIR_FstClusHI(self, cluster_in: int):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_FstClusHI     | 20               | 2             |
        ------------------------------------------------------
        High word of first data cluster number for file/directory described
        by this entry. Only valid for volumes formatted FAT32. Must be set to
        0 on volumes formatted FAT12/FAT16.

        :param cluster_in: int: High word of first data cluster number for
        file/directory described by this entry.
        """
        struct.pack_into(
            f"{self.endianness}H", self.data,
            20, cluster_in)

    @property
    def DIR_WrtTime(self) -> timestamp.Timestamp:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_WrtTime       | 22               | 2             |
        ------------------------------------------------------
        Last modification (write) time. Value must be equal to DIR_CrtTime at
        file creation.

        Directory entry timestamps are 16-bit values with a granularity of 2
        seconds. Contents of the DIR_CrtTime and DIR_WrtTime must be in the
        following format:
          - 0:4 contain elapsed seconds – as a count of 2-second increments
            (valid range: 0..29 inclusive allowing representation of 0 through
            58 seconds)
          - 5:10 represent number of minutes (valid range: 0..59 inclusive)
          - 11:15 represent hours (valid range: 0..23 inclusive)
        The valid time range is from Midnight 00:00:00 to 23:59:58.

        :return: int: Last modification (write) time.
        """
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 22)[0]

    @DIR_WrtTime.setter
    def DIR_WrtTime(self, time_in: int | timestamp.Timestamp):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_WrtTime       | 22               | 2             |
        ------------------------------------------------------
        Last modification (write) time. Value must be equal to DIR_CrtTime at
        file creation.

        Directory entry timestamps are 16-bit values with a granularity of 2
        seconds. Contents of the DIR_CrtTime and DIR_WrtTime must be in the
        following format:
          - 0:4 contain elapsed seconds – as a count of 2-second increments
            (valid range: 0..29 inclusive allowing representation of 0 through
            58 seconds)
          - 5:10 represent number of minutes (valid range: 0..59 inclusive)
          - 11:15 represent hours (valid range: 0..23 inclusive)
        The valid time range is from Midnight 00:00:00 to 23:59:58.

        :param time_in: int: Last modification (write) time.
        """
        struct.pack_into(
            f"{self.endianness}H", self.data, 22,
            time_in.time if isinstance(time_in,
                    timestamp.Timestamp) else time_in)

    @property
    def DIR_WrtDate(self) -> int:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_WrtDate       | 24              | 2             |
        ------------------------------------------------------
        Last modification (write) date. Value must be equal to DIR_CrtDate at
        file creation.

        Contents of the DIR_CrtDate, DIR_LstAccDate, and DIR_WrtDate fields
        must be in the following format:
          - 0:4 represent the day of the month (valid range: 1..31 inclusive)
          - 5:8 represent the month of the year (1 = January, 12 = December,
            valid range: 1..12 inclusive)
          - 9:15 are the count of years from 1980 (valid range: 0..127
            inclusive allowing representation of years 1980 through 2107)

        :return: int: Last modification (write) date.
        """
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 24)[0]

    @DIR_WrtDate.setter
    def DIR_WrtDate(self, date_in: int | timestamp.Timestamp):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_WrtDate       | 24              | 2             |
        ------------------------------------------------------
        Last modification (write) date. Value must be equal to DIR_CrtDate at
        file creation.

        Contents of the DIR_CrtDate, DIR_LstAccDate, and DIR_WrtDate fields
        must be in the following format:
          - 0:4 represent the day of the month (valid range: 1..31 inclusive)
          - 5:8 represent the month of the year (1 = January, 12 = December,
            valid range: 1..12 inclusive)
          - 9:15 are the count of years from 1980 (valid range: 0..127
            inclusive allowing representation of years 1980 through 2107)

        :param date_in: int: Last modification (write) date.
        """
        struct.pack_into(
            f"{self.endianness}H", self.data, 24,
            date_in.date if isinstance(date_in,
                    timestamp.Timestamp) else date_in)

    @property
    def DIR_FstClusLO(self) -> int:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_FstClusLO     | 26               | 2             |
        ------------------------------------------------------
        Low word of first data cluster number for file/directory described by
        this entry.

        :return: int: Low word of first data cluster number for
        file/directory described by this entry.
        """
        return struct.unpack_from(
            f"{self.endianness}H",
            self.data, 26)[0]

    @DIR_FstClusLO.setter
    def DIR_FstClusLO(self, cluster_in: int):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_FstClusLO     | 26               | 2             |
        ------------------------------------------------------
        Low word of first data cluster number for file/directory described by
        this entry.

        :param cluster_in: int: Low word of first data cluster number for
        file/directory described by this entry.
        """
        struct.pack_into(
            f"{self.endianness}H", self.data,
            26, cluster_in)

    @property
    def DIR_FileSize(self) -> int:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_FileSize      | 28               | 4             |
        ------------------------------------------------------
        32-bit quantity containing size in bytes of file/directory described
        by this entry.

        :return: int: Size in bytes of file/directory described
        by this entry.
        """
        return struct.unpack_from(
            f"{self.endianness}L",
            self.data, 28)[0]

    @DIR_FileSize.setter
    def DIR_FileSize(self, size_in: int):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        DIR_FileSize      | 28               | 4             |
        ------------------------------------------------------
        32-bit quantity containing size in bytes of file/directory described
        by this entry.

        :param size_in: int: Size in bytes of file/directory described
        by this entry.
        """
        if (self.DIR_Attr & self.ATTR_DIRECTORY and
            size_in > self.MAX_DIR):
            raise ValueError(
                f"Error: Directory Size Exceeds Maximum!\n"
                f"Size: {size_in}\nMaximum: {self.MAX_DIR}")
        elif size_in > self.MAX_FILE:
            raise ValueError(
                f"Error: File Size Exceeds Maximum!\n"
                f"Size: {size_in}\nMaximum: {self.MAX_FILE}")

        struct.pack_into(
            f"{self.endianness}L", self.data,
            28, size_in)

    @property
    def DIR_FstClusAddress(self) -> int:
        return self.__data_offset + (
                (self.DIR_FstClus - 2) * self.__fat.cluster_size)

    def allocate(self, data_in: bytearray | memoryview = None,
                 name_in: str = "", attributes_in: int = 0x0,
                 parent_in: 'Directory' = None) -> int:
        name_in = name_in.lstrip("/").lstrip("\\")

        # Split the path into its parts. If there is more than one part, then
        # allocate in the next directory.
        path = re.split(r"[\/]", name_in)
        if len(path) > 1:
            for directory in self:
                if (directory.DIR_Name == path[0] and
                        directrory.DIR_Attr & self.ATTR_DIRECTORY):
                    return directory.allocate(
                        data_in, "/".join(path[1:]), attributes_in, self)
            else:
                raise ValueError(
                    f"Error: File or Directory Not Found: {path[0]}")

        # Root Directory
        # The root directory is a special container file created during volume
        # initialization (format) and,therefore, always present on the
        # formatted volume. Only the root directory can contain an entry with
        # the DIR_Attr field contents equal to ATTR_VOLUME_ID.
        elif attributes_in & self.ATTR_VOLUME_ID:
            raise ValueError(
                f"Error: Cannot Allocate Directory With Flags: {attributes_in}\n"
                f"Indide another directory..")

        else:
            # Directory Creation
            if attributes_in & self.ATTR_DIRECTORY:
                return self.allocate_directory(name_in, attributes_in, parent_in)

            # File allocation
            else:
                return self.allocate_file(data_in, name_in, attributes_in)

    def allocate_directory(self, name_in: str = "",
        attributes_in: int = 0x0, parent_in: 'Directory' = None) -> int:

        # Get the directory
        entry = self.__next

        # Set the name of the new directory.
        entry.DIR_Name = name_in

        # When a new directory is created, the file system
        # implementation must ensure the following:
        entry.DIR_Attr = attributes_in | self.ATTR_DIRECTORY

        # The DIR_FileSize must be set to 0
        entry.DIR_FileSize = 0

        # At least one cluster must be allocated – the contents of the
        # DIR_FstClusLO and DIR_FstClusHI fields must refer to the first
        # allocated cluster number. If only a single cluster is allocated, the
        # corresponding file allocation table entry must indicate end-of-file
        # condition.
        if entry.DIR_Name == "." or entry.DIR_Name == "..":
            if entry.DIR_Name == ".":
                entry.__copy(self)

            elif entry.DIR_Name == "..":
                if parent_in is not None and isinstance(parent_in, Directory):
                    entry.__copy(parent_in)
                else:
                    raise ValueError(
                        f"Error: parent_in must be specified "
                        f"for directory: {entry.DIR_Name}")

        else:
            # Allocate a new entry.
            entry.DIR_FstClus = self.__fat.allocate()

            # Except for the root directory, each directory must contain the
            # following two entries at the beginning of the directory:

            # The first directory entry must have a directory name set to “.”.
            # This dot entry refers to the current directory. Rules listed
            # above for the DIR_Attr field and DIR_FileSize field must be
            # followed. Since the dot entry refers to the current directory
            # (the one containing the dot entry), the contents of the
            # DIR_FstClusLO and DIR_FstClusHI fields must be the same as that
            # of the current directory. All date and time fields must be set
            # to the same value as that for the containing directory.
            entry.allocate_directory(name_in=".")

            # The second directory entry must have the directory name set to
            # “..”. This dotdot entry refers to the parent of the current
            # directory. Rules listed above for the DIR_Attr field and
            # DIR_FileSize field must be followed. Since the dotdot entry
            # refers to the parent of the current directory (the one containing
            # the dotdot entry), the contents of the DIR_FstClusLO and
            # DIR_FstClusHI fields must be the same as that of the parent of
            # the current directory. If the parent of the current directory is
            # the root directory (see below), the DIR_FstClusLO and
            # DIR_FstClusHI contents must be set to 0. All date and time fields
            # must be set to the same value as that for the containing
            # directory.
            entry.allocate_directory(name_in="..", parent_in=self)

        # Return the allocated cluster number.
        return entry.DIR_FstClus

    def allocate_file(self, data_in: bytearray | memoryview = None,
                      name_in: str = "",
                      attributes_in: int = 0x0) -> int:
        size = len(data_in) if data_in is not None else 0x1000

        entry = self.__next

        # Set the name of the new directory.
        entry.DIR_Name = name_in

        # When a new directory is created, the file system
        # implementation must ensure the following:
        entry.DIR_Attr = attributes_in

        # The DIR_FileSize must be set to the length of the file data
        entry.DIR_FileSize = size

        # The cluster number of the first cluster of the file is recorded in
        # the directory entry associated with the file. For zero-length files,
        # the first cluster number in the associated directory entry is set to
        # 0. The file allocation table entry corresponding to the first
        # allocated cluster for a file either indicates that this is the
        # sole/last allocated cluster for the file or contains the cluster
        # number for the next allocated cluster.
        entry.DIR_FstClus = self.__fat.allocate(data_in)

        # Update the
        entry.__created()

        return entry.DIR_FstClus

    def read(self) -> bytearray:
        self.__accessed()

    def write(self, data_in: bytearray | memoryview):
        self.__modified()

    @property
    def __next(self) -> 'Directory':
        for directory in self:
            if directory.free:
                return directory
        return None

    def __modified(self):
        now = timestamp.Timestamp()
        self.DIR_WrtTime = now
        self.DIR_WrtDate = now

    def __accessed(self):
        now = timestamp.Timestamp()
        self.DIR_LstAccDate = now

    def __created(self):
        now = timestamp.Timestamp()
        self.DIR_CrtTimeTenth = now
        self.DIR_CrtTime = now
        self.DIR_CrtDate = now

    def __copy(self, other_in: 'Directory'):
        self.DIR_Attr = other_in.DIR_Attr
        self.DIR_CrtTimeTenth = other_in.DIR_CrtTimeTenth
        self.DIR_CrtTime = other_in.DIR_CrtTime
        self.DIR_CrtDate = other_in.DIR_CrtDate
        self.DIR_FstClus = other_in.DIR_FstClus
        self.DIR_LstAccDate = other_in.DIR_LstAccDate
        self.DIR_WrtTime = other_in.DIR_WrtTime
        self.DIR_WrtDate = other_in.DIR_WrtDate
        self.DIR_FileSize = other_in.DIR_FileSize

    @property
    def __length(self) -> int:
        return int(self.__fat.sector_size / self.LENGTH)

    def __getitem__(self, index_in: int) -> 'Directory':
        if index_in < self.__length:
            return Directory(
                self.disk, self.endianness,
                self.__fat, self.__data_offset,
                self.DIR_FstClusAddress + index_in * self.LENGTH)
        else:
            return None

    def __iter__(self):
        return iter([self[i] for i in range(self.__length)])



