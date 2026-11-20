#!/bin/env python3
import os, math, sys
if os.path.join(os.getcwd(), "lib") not in sys.path:
    sys.path.append(os.path.join(os.getcwd(), "lib"))
import partition, boot, fat, fsinfo, root, bpb, directory


# =============================================================================
# Volume
# -----------------------------------------------------------------------------
#
#
# =============================================================================
class Volume(partition.Partition):
    """
    """
    def __init__(self, file_in: str = None, initialize_in: bool = False):
        """
        :param file_in: str: The filename of the disk.
        """
        self.__boot = []
        self.__fsinfo = []
        self.__fat = []
        self.__root = []
        self.__file = None

        if file_in is not None:
            print("Reading Partition...")
            data = self.load(file_in)

            # All the FAT file systems were originally developed for the IBM PC
            # machine architecture. Hence, on disk data structures for the FAT
            # format are all “little endian.”
            #
            # The most important thing is that data structures in the FAT filesystem
            # on the storage is stored in little endian since it was developed by IBM
            # for the x86 architecture. Which is little endian.
            self.__boot.append(boot.BootSector(data, "<"))

            if not self.__boot[0].valid:
                self.__boot[0].format()

                # Inform the user if the partition is unformatted or invalid.
                print("File System is unformatted or invalid. "
                      "Recommend (re)formatting.")

            super().__init__(
                data, "<",
                self.__boot[0].bpb.BPB_SecPerClus,
                self.__boot[0].bpb.BPB_BytsPerSec,
                initialize_in)

    def format(self, label_in: str = bpb.BPB._NO_VOLLAB):
        print("Formatting Partition...")
        self.__reset()

        # There are three FAT types, FAT12, FAT16 and FAT32, need to be
        # determined on mount a FAT volume. However, there are considerable
        # confusions over determination of FAT types, and they lead various
        # degree of errors. In fact, it is a quite simple procedure. The FAT
        # type is determined by the count of clusters on the volume and NOTHING
        # ELSE.
        self.__boot.append(
            boot.BootSector(self.data, "<"))
        self.__boot[0].format(label_in)

        if (self.__boot[0].bpb.type == bpb.BPB._TYPE["FAT12"] or
            self.__boot[0].bpb.type == bpb.BPB._TYPE["FAT16"]):

            # Configure the FATs
            for i in range(0):
                # Initialize the FAT.
                self.__fat.append(fat.FAT(
                    self.__boot[0].bpb.total_clusters,
                    self.data,
                    self.endianness,
                    self.__boot[0].bpb.BPB_BytsPerSec * (
                        self.__boot[0].bpb.BPB_RsvdSecCnt + (
                            i * self.__boot[0].bpb.BPB_FATSz32)),
                    i + 1))
                self.__fat[i].format()
                self.__boot[0].bpb.BPB_NumFATs = i + 1
                
            # Root Directory
            # The root directory is a special container file created during volume
            # initialization (format) and, therefore, always present on the formatted
            # volume.
            #
            # On FAT12 and FAT16 volumes, the root directory must immediately follow the
            # last file allocation table. The location of the first sector of the root
            # directory is computed as below:
            # FirstRootDirSecNum = BPB_ResvdSecCnt + (BPB_NumFATs * BPB_FATSz16)
            #
            # The size of the root directory on FAT12 and FAT16 volumes is computed using
            # the contents of the BPB_RootEntCnt field.
            self.__root.append(
                root.RootDirectory16(
                    self.data,
                    self.endianness,
                    self.__boot[0].bpb.BPB_RsvdSecCnt + (
                            self.__boot[0].bpb.BPB_NumFATs *
                            self.__boot[0].bpb.BPB_FATSz16),
                    self.__boot[0].bpb.BPB_BytsPerSec))
            self.__root[0].format()

        else:
            # Add a backup boot sector.
            self.__boot[0].bpb.BPB_BkBootSec = 6
            self.__boot.append(
                boot.BootSector(
                    self.data,
                    self.endianness,
                    self.__boot[0].bpb.BPB_BkBootSec,
                    self.__boot[0].bpb.BPB_BytsPerSec))
            self.__boot[1].format(label_in)
            self.__boot[1].bpb.BPB_FSInfo = 7
            self.__boot[0].bpb.BPB_BkBootSec = self.__boot[1].bpb.BPB_BkBootSec = 6
            self.__boot[0].bpb.BPB_NumFATs = self.__boot[1].bpb.BPB_NumFATs = len(self.__boot)

            # Configure and format the FATS.
            for i in range(2):
                # Initialize the FAT.
                table = i + 1
                self.__fat.append(fat.FAT(
                    self.__boot[0].bpb.data_clusters,
                    self.data,
                    self.endianness,
                    self.__boot[0].bpb.BPB_BytsPerSec * (
                        self.__boot[0].bpb.BPB_RsvdSecCnt + (
                            i * self.__boot[0].bpb.BPB_FATSz32)),
                    self.__boot[0].bpb.BPB_BytsPerSec,
                    self.__boot[0].bpb.BPB_SecPerClus,
                    table))
                self.__fat[i].format()
                for bs in self.__boot:
                    bs.bpb.BPB_NumFATs = table

            # Format the FSInfo Sectors
            for i, sector in enumerate([1, 7]):
                self.__fsinfo.append(
                    fsinfo.FSInfo(
                        self.data,
                        self.endianness,
                        sector,
                        self.__boot[0].bpb.BPB_BytsPerSec))
                self.__fsinfo[i].format(
                    self.__fat[0].free_count,
                    self.__fat[0].first_free)

            # Root Directory
            # The root directory is a special container file created during
            # volume initialization (format) and, therefore, always present on
            # the formatted volume.
            #
            # On volumes formatted FAT32, the root directory can be of variable size. The
            # location of the first cluster of the root directory on the FAT32 volume is
            # stored in the BPB_RootClus field.
            #
            # Only the root directory can contain an entry with the DIR_Attr field contents
            # equal to ATTR_VOLUME_ID.
            #
            # There is no name for the root directory (on most operating system
            # implementations, the implied name “/” is used). Further, the root directory
            # does not have any associated date/time stamps. Lastly, the root directory
            # does not contain either the dot or dotdot entries.
            self.__root.append(
                directory.Directory(
                    self.data[self.__boot[0].bpb.data_offset:],
                    self.endianness,
                    self.__fat[0],
                    self.__boot[0].bpb.BPB_RootClus *
                    self.__boot[0].bpb.BPB_SecPerClus *
                    self.__boot[0].bpb.BPB_BytsPerSec,
                    self.__boot[0].bpb.BPB_BytsPerSec,
                    attributes_in=directory.Directory.ATTR_VOLUME_ID))

    @property
    def valid(self) -> bool:
        return self.__boot[0].valid

    @property
    def boot(self) -> memoryview:
        return self.__boot[0].bpb.BS_BootCode

    def allocate(self, data_in: bytearray | memoryview = None, name_in: str = "",
                 attributes_in: int = 0x0):
        # If the allocation is data-less, then it must be a directory.
        cluster = self.__root[0].allocate(data_in, name_in, attributes_in)

        # Update the FSInfo
        self.__update_fsinfo(cluster)

    def modify(self, data_in: bytearray | memoryview, cluster_in: int):
        pass

    def read(self):
        pass

    def write(self):
        pass

    def __update_fsinfo(self, cluster_in: int):
        for fsinfo in self.__fsinfo:
            fsinfo.FSI_Free_count = self.__fat[0].free_count
            fsinfo.FSI_Nxt_Free = cluster_in

    def __reset(self):
        self.__boot = []
        self.__fsinfo = []
        self.__fat = []
        self.__root = []

    def sync(self, file_in: str = None):
        file_in = file_in if file_in is not None else self.__file
        if file_in is not None:
            print(f"Syncing {len(self.data)} Byte(s) To: {file_in}")
            with open(file_in, 'wb') as file:
                try:
                    file.write(self.data)

                finally:
                    file.close()

        else:
            print(
                f"Warning: No File Loaded As Disk: {file_in}")

    def load(self, file_in: str) -> bytearray:
        file_in = os.path.abspath(file_in)
        print(f"Reading File: {file_in}")
        with open(file_in, 'rb') as file:
            try:
                data = bytearray(file.read())
                print(f"{len(data)} Byte(s) Read...")
                self.__file = file_in
                return data

            finally:
                file.close()


if __name__ == '__main__':
    vol = Volume("2G.img")
    # if vol.valid:
    #     print("Dumping Boot Code...")
    #     with open("boot.bin", "wb") as file:
    #         try:
    #             file.write(vol.boot)
    #         finally:
    #             file.close()
    #
    # else:
    vol.format()

    # Test Allocations...
    vol.allocate(
        name_in="/TEST",
        attributes_in=directory.Directory.ATTR_DIRECTORY)

    vol.allocate(
        data_in=bytearray("Test. 1, 2, 3.".encode("utf-8")),
        name_in="/TEST/test.txt")

    vol.sync("FAT32.img")