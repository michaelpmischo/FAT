#!/usr/bin/env python3
import struct, os
import data, sector, bpb, bpb16, bpb32



# =============================================================================
# Boot Sector
# -----------------------------------------------------------------------------
# The Boot Sector is located in the first sector of the volume in the Reserved
# Region. This sector is sometimes called the “boot sector” or the “0 th
# sector”.
#
# =============================================================================
class BootSector(sector.Sector):
    def __init__(self, data_in: bytearray | memoryview, endianness_in: str,
                 sector_in: int = 0, size_in: int = int(0.5 * data.Data._KiB)):
        super().__init__(data_in, endianness_in, sector_in, size_in)

        # This section describes the determination of values for specific
        # fields in the BPB during volume initialization for a given target
        # volume. FAT implementations must be capable of mounting media with
        # all legal values for fields comprising the BPB.
        if not self.valid:
            # Floppy disks are formatted as FAT12. A simple (pre-specified)
            # table determines the BPB structure contents for floppy media.
            # Note that media size for FAT12 volumes must be <= 4MB.
            if self.disk_size <= 4 * data.Data._MiB:
                self.__bpb = BPB16(
                    data_in, endianness_in, sector_in, size_in)

            # For 512 byte sector sized media: if volume size is < 512 MB, the
            # volume is formatted FAT16
            elif self.disk_size < 512 * data.Data._MiB:
                self.__bpb = BPB16(
                    data_in, endianness_in, sector_in, size_in)

            # Else it is formatted FAT32. It is possible to override the
            # default FAT type selection.
            else:
                self.__bpb = bpb32.BPB32(
                    data_in, endianness_in, sector_in, size_in)

        else:
            # Determination of FAT type (FAT12, FAT16, or FAT32) is dependent on the
            # number of clusters (described in Section 3.5 below). This section
            # describes the determination of values for specific fields in the BPB
            # during volume initialization for a given target volume. FAT
            # implementations must be capable of mounting media with all legal values
            # for fields comprising the BPB. The FAT type is determined solely by the
            # count of clusters on the volume (CountOfClusters).
            self.__bpb = bpb32.BPB32(data_in, endianness_in, sector_in, size_in)

            # Note the following:
            # A FAT12 volume cannot contain more than 4084 clusters.
            # A FAT16 volume cannot contain less than 4085 clusters or more than
            # 65,524 clusters.
            if self.__bpb.type == bpb.BPB._TYPE["FAT12"]:
                # TODO: Create a FAT12 BPB.
                self.__bpb = bpb16.BPB12(data_in, endianness_in, sector_in, size_in)

            elif self.__bpb.type == bpb.BPB._TYPE["FAT16"]:
                self.__bpb = bpb16.BPB16(data_in, endianness_in, sector_in, size_in)

    def format(self, volume_label_in: str = bpb.BPB._NO_VOLLAB):
        self.__bpb.format(volume_label_in)

        # At this point, it is assumed that BPB_RootEntCnt, BPB_RsvdSecCnt, and
        # BPB_NumFATs are appropriately set. It is also assumed that DskSize is
        # the size of the volume that will be reflected in BPB_TotSec32 or
        # BPB_TotSec16.
        self.BS_JmpBoot[0] = 0xEB
        if (self.bpb.BS_FilSysType == "FAT12" or
            self.bpb.BS_FilSysType == "FAT16"):
            self.BS_JmpBoot[1] = 0x58
            self.BS_JmpBoot[2] = 0x90
        else:
            self.BS_JmpBoot[1] = 0x58
            self.BS_JmpBoot[2] = 0x90

        # There are many misconceptions about this field. It is only a name
        # string.
        self.BS_OEMName = os.path.basename(__file__)

    @property
    def BS_JmpBoot(self) -> memoryview:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        BS_JmpBoot       | 0                 | 3             |
        ------------------------------------------------------
        Jump instruction to boot code. This field has two allowed forms:
          1. (JMP 8-Bit Address)
             jmpBoot[0] = 0xEB, jmpBoot[1] = 0x??, jmpBoot[2] = 0x90

          2. (JMP 16-Bit Address)
             jmpBoot[0] = 0xE9, jmpBoot[1] = 0x??, jmpBoot[2] = 0x??

        0x?? indicates that any 8-bit value is allowed in that byte. What
        this forms is a three-byte Intel x86 unconditional branch (jump)
        instruction that jumps to the start of the operating system
        bootstrap code. This code typically occupies the rest of sector 0
        of the volume following the BPB and possibly other sectors. Either
        of these forms is acceptable. JmpBoot[0] = 0xEB is the more
        frequently used format.

        :return: BS_JmpBoot: list[byte]
        """
        return self.data[0:3]

    @BS_JmpBoot.setter
    def BS_JmpBoot(self, instruction_in: int | bytearray | memoryview):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        BS_JmpBoot       | 0                 | 3             |
        ------------------------------------------------------
        Jump instruction to boot code. This field has two allowed forms:
          1. (JMP 8-Bit Address)
             jmpBoot[0] = 0xEB, jmpBoot[1] = 0x??, jmpBoot[2] = 0x90

          2. (JMP 16-Bit Address)
             jmpBoot[0] = 0xE9, jmpBoot[1] = 0x??, jmpBoot[2] = 0x??

        0x?? indicates that any 8-bit value is allowed in that byte. What
        this forms is a three-byte Intel x86 unconditional branch (jump)
        instruction that jumps to the start of the operating system
        bootstrap code. This code typically occupies the rest of sector 0
        of the volume following the BPB and possibly other sectors. Either
        of these forms is acceptable. JmpBoot[0] = 0xEB is the more
        frequently used format.

        :param instruction_in: int: The x86 boot jump instruction to the
        operating system's boot code.
        """

        # Validate Inputs
        if isinstance(instruction_in, int):
            instruction_in = (
                (instruction_in & 0xFF0000) >> 16,
                (instruction_in & 0xFF00 >> 8),
                (instruction_in & 0xFF))

        elif (isinstance(instruction_in, bytearray) or
              isinstance(instruction_in, memoryview)):
            instruction_in = instruction_in[0:3]

        else:
            raise ValueError(
                f"Error: Invalid Instruction: "
                f"{type(instruction_in).__name__}")

        if instruction_in[0] == 0xE9 or (instruction_in[0] == 0xEB and instruction_in[2] == 90):
            struct.pack_into(
                f"{self.endianness}3B", self.data,
                0, instruction_in)
        else:
            raise ValueError(
                f"Error: Invalid jump instruction to boot code. "
                f"{instruction_in}\n"
                f"This field has tww allowed forms:\n "
                f"\tjmpBoot[0] = 0xEB??90 | 0xE9????")

    @property
    def BS_OEMName(self) -> str:
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        BS_OEMName       | 3                 | 8             |
        ------------------------------------------------------
        “MSWIN4.1” There are many misconceptions about this field. It is
        only a name string. Microsoft operating systems don’t pay any
        attention to this field. Some FAT drivers do. This is the reason
        that the indicated string, “MSWIN4.1”, is the recommended setting,
        because it is the setting least likely to cause compatibility
        problems. If you want to put something else in here, that is your
        option, but the result may be that some FAT drivers might not
        recognize the volume. Typically, this is some indication of what
        system formatted the volume.

        :return: BS_OEMName: str
        """
        return struct.unpack_from(
            f"{self.endianness}8s",
            self.data, 3)[0].rstrip(b"\x00").decode('ascii')

    @BS_OEMName.setter
    def BS_OEMName(self, name_in: str):
        """
        Name             | Offset (Byte)     | Size (Bytes)  |
        ------------------------------------------------------
        BS_OEMName       | 3                 | 8             |
        ------------------------------------------------------
        “MSWIN4.1” There are many misconceptions about this field. It is
        only a name string. Microsoft operating systems don’t pay any
        attention to this field. Some FAT drivers do. This is the reason
        that the indicated string, “MSWIN4.1”, is the recommended setting,
        because it is the setting least likely to cause compatibility
        problems. If you want to put something else in here, that is your
        option, but the result may be that some FAT drivers might not
        recognize the volume. Typically, this is some indication of what
        system formatted the volume.

        :param name_in: str: BS_OEMName: str
        """
        struct.pack_into(
            f"{self.endianness}8s", self.data,
            3, name_in.encode("ascii"))

    @property
    def MAX(self) -> int:
        return self.bpb.DataClus + 1

    @property
    def bpb(self) -> bpb.BPB:
        return self.__bpb

    @property
    def valid(self) -> bool:
        """
        The boot sector needs to be valid only if the boot signature
        (BS_Sign) contains 0xAA55. If not, the boot sector is invalid.
        Many FAT documents describe about this field, "Boot signature is
        put at the end of the boot sector". But this only applies for a
        sector size of 512. The Signature must alway be located at offset
        510.

        :return: bool: True if the Boot Sector is valid else False
        """
        return (struct.unpack_from(
            f"{self.endianness}H", self.data, 510)[0] ==
                bpb.BPB._SIGNATURE)