#!/bin/python
import datetime


class Timestamp(object):
    """

    """
    __BASE_YEAR = 1980
    __SECOND_RES = 2
    __MICROSECOND_PER_TENTH = 100000
    __BITS = {
        "DATE": {
            "SHIFT": 32,
            "MASK": 0xFFFF00000000,
        },
        "YEAR": {
            "SHIFT": 41,
            "MASK": 0xFE0000000000,
        },
        "MONTH": {
            "SHIFT": 37,
            "MASK": 0x01E000000000,
        },
        "DAY": {
            "SHIFT": 32,
            "MASK": 0x001F00000000,
        },
        "TIME": {
            "SHIFT": 16,
            "MASK": 0x0000FFFF0000,
        },
        "HOUR": {
            "SHIFT": 27,
            "MASK": 0x0000F8000000,
        },
        "MINUTE": {
            "SHIFT": 21,
            "MASK": 0x000007E00000,
        },
        "SECOND": {
            "SHIFT": 16,
            "MASK": 0x0000001F0000,
        },
        "ID": {
            "SHIFT": 16,
            "MASK": 0xFFFFFFFF0000,
        },
        "TENTHS":{
            "SHIFT": 0,
            "MASK": 0x00000000FFFF,
        }
    }

    def __init__(self, date_in: int = 0, time_in: int = 0, tenths_in: int = 0):
        self.__value = 0

        if date_in or time_in or tenths_in:
            self.date = date_in
            self.time = time_in
            self.tenths = tenths_in
        else:
            self.update()

    @property
    def value(self) -> int:
        return self.__value

    @property
    def id(self) -> int:
        return self.__get("ID")

    @property
    def date(self) -> int:
        return self.__get("DATE")

    @date.setter
    def date(self, date_in: int):
        self.__set("DATE", date_in)

    @property
    def year(self) -> int:
        """
        Bit positions 9 through 15 are the count of years from 1980
        (valid range: 0..127 inclusive allowing representation of years
        1980 through 2107)

        :return: int: The Year.
        """
        return self.__get("YEAR") + self.__BASE_YEAR

    @year.setter
    def year(self, year_in: int):
        """
        Bit positions 9 through 15 are the count of years from 1980
        (valid range: 0..127 inclusive allowing representation of years
        1980 through 2107)

        :param year_in: int: The Year.
        """
        if 1980 <= year_in <= 2107:
            self.__set("YEAR", year_in - self.__BASE_YEAR)
        else:
            raise ValueError(
                f"Error: Invalid YEar: {year_in}\n"
                f"Valid range: 1980..2107 inclusive")

    @property
    def month(self) -> int:
        """
        Bit positions 5 through 8 represent the month of the year
        (1 = January, 12 = December, valid range: 1..12 inclusive)

        :return: int: The month of the year, where 1 = January,
        12 = December.
        """
        return self.__get("MONTH")

    @month.setter
    def month(self, month_in: int):
        """
        Bit positions 5 through 8 represent the month of the year
        (1 = January, 12 = December, valid range: 1..12 inclusive)

        :param month_in: int: The month of the year, where 1 = January,
        12 = December.
        """
        if 1 <= month_in <= 12:
            self.__set("MONTH", month_in)
        else:
            raise ValueError(
                f"Error: Invalid Month: {month_in}\n"
                f"Valid range: 1..12 inclusive")

    @property
    def day(self) -> int:
        """
        Bit positions 0 through 4 represent the day of the month (valid
        range: 1..31 inclusive)

        :return: int: tThe Day of the Month.
        """
        return self.__get("DAY")

    @day.setter
    def day(self, day_in: int):
        """
        Bit positions 0 through 4 represent the day of the month (valid
        range: 1..31 inclusive)

        :param day_in: int: tThe Day of the Month.
        """
        if 1 <= day_in <= 31:
            self.__set("DAY", day_in)
        else:
            raise ValueError(
                f"Error: Invalid Day: {day_in}\n"
                f"Valid range: 1..31 inclusive")

    @property
    def time(self) -> int:
        """
        Directory entry timestamps are 16-bit values with a granularity of 2
        seconds. Contents of the DIR_CrtTime and DIR_WrtTime must be in the
        the time format.

        :return: The 16-bit value of the time for FAT timestamps.
        """
        return self.__get("TIME")

    @time.setter
    def time(self, time_in: int):
        """
        Directory entry timestamps are 16-bit values with a granularity of 2
        seconds. Contents of the DIR_CrtTime and DIR_WrtTime must be in the
        the time format.

        :param time_in: The 32-bit value of the time and date for FAT
        timestamps.
        """
        self.__set("TIME", time_in)

    @property
    def hour(self) -> int:
        """
        Bit positions 11 through 15 represent hours (valid range: 0..23
        inclusive)

        :return: int: The hor of the day. (valid range: 0..23
        inclusive)
        """
        return self.__get("HOUR")

    @hour.setter
    def hour(self, hour_in: int):
        """
        Bit positions 11 through 15 represent hours (valid range: 0..23
        inclusive)

        :param hour_in: int: The hor of the day. (valid range: 0..23
        inclusive)
        """
        if 0 <= hour_in <= 23:
            self.__set("HOUR", hour_in)
        else:
            raise ValueError(
                f"Error: Invalid Hour: {hour_in}\n"
                f"Valid range: 0..23 inclusive")

    @property
    def minute(self) -> int:
        """
        Bit positions 5 through 10 represent number of minutes of the hour
        (valid range: 0..59 inclusive)

        :return: int: The minute of the hour.
        """
        return self.__get("MINUTE")

    @minute.setter
    def minute(self, minutes_in: int):
        """
        Bit positions 5 through 10 represent number of minutes of the hour
        (valid range: 0..59 inclusive)

        :param minutes_in: int: The minute of the hour.
        """
        if 0 <= minutes_in <= 59:
            self.__set("MINUTE", minutes_in)
        else:
            raise ValueError(
                f"Error: Invalid Minute: {minutes_in}\n"
                f"Valid range: 0..59 inclusive")

    @property
    def second(self) -> int:
        """
        Bit positions 0 through 4 contain elapsed seconds – as a count of
        2-second increments (valid range: 0..29 inclusive allowing
        representation of 0 through 58 seconds)

        :return: int: The seconds of the minute. Resolution: 2sec.
        """
        return self.__get("SECOND") * self.__SECOND_RES

    @second.setter
    def second(self, seconds_in: int):
        """
        Bit positions 0 through 4 contain elapsed seconds – as a count of
        2-second increments (valid range: 0..29 inclusive allowing
        representation of 0 through 58 seconds)

        :param seconds_in: int: The Second of the Minute. This will be rounded
        down to nearest 2sec interval.
        """
        if 0 <= seconds_in <= 59:
            self.__set("SECOND", seconds_in // self.__SECOND_RES)
        else:
            raise ValueError(
                f"Error: Invalid Seconds: {seconds_in}\n"
                f"Valid range: 0..59 inclusive")

    @property
    def tenths(self) -> int:
        return self.__get("TENTHS")

    @tenths.setter
    def tenths(self, temths_in: int):
        self.__set("TENTHS", temths_in)

    @property
    def microsecond(self) -> int:
        return self.__get("TENTHS") * self.__MICROSECOND_PER_TENTH

    @microsecond.setter
    def microsecond(self, microseconds_in: int):
        self.__set("TENTHS", microseconds_in // self.__MICROSECOND_PER_TENTH)

    @property
    def datetime(self) -> datetime.datetime:
        return datetime.datetime(
            year=self.year, month=self.month,
            day=self.day, hour=self.hour,
            minute=self.minute, second=self.second)

    def update(self):
        date = datetime.datetime.now()
        self.year = date.year
        self.month = date.month
        self.day = date.day
        self.hour = date.hour
        self.minute = date.minute
        self.second = date.second
        self.microsecond = date.microsecond

    def __get(self, key_in: str) -> int:
        key_in = key_in.upper()
        if key_in in self.__BITS.keys():
            return ((self.__value & self.__BITS[key_in]["MASK"]) >>
                    self.__BITS[key_in]["SHIFT"])
        else:
            raise ValueError(
                f"Error: Invalid Key: {key_in}")

    def __set(self, key_in: str, value_in: int):
        key_in = key_in.upper()
        if key_in in self.__BITS.keys():
            if isinstance(value_in, int):
                self.__value |= ((value_in << self.__BITS[key_in]["SHIFT"]) &
                                self.__BITS[key_in]["MASK"])
            else:
                raise ValueError(
                    f"Error: Invalid Value Type: {type(value_in).__name__}\n"
                    f"Must Be Integer")
        else:
            raise ValueError(
                f"Error: Invalid Key: {key_in}")