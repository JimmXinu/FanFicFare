#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A pure Python GIF metadata extractor.
Supports adjustable detail to fine-tune performance.

Example code and full epydoc docstrings included.

Uses:
 - Identifying whether a GIF is static or animated.
 - Extracting the dimensions, pixel aspect ratio, number of frames, loop count,
    global palette or palette size, and background color.
 - Extracting comments and other plaintext.
 - Testing for various structural errors.

TODO:
 - Provide basic support for XMP Metadata extraction
   - http://en.wikipedia.org/wiki/Extensible_Metadata_Platform#Location_in_file_types
   - http://www.matthewflickinger.com/lab/whatsinagif/bits_and_bytes.asp
   - Generate test GIF with http://code.google.com/p/python-xmp-toolkit/

Changelog:
 - 0.2.2: Audited the code and made some corrections.
 - 0.2.1: 40% speed improvement (went from 15 to 9 seconds for 1000 images)
 - 0.2.0: Feature-complete
 - 0.1.0: Initial release
"""

__appname__ = "gif.py"
__author__  = "Stephan Sokolow (deitarion/SSokolow)"
__version__ = "0.2.2"
__license__ = "PSF License 2.4 or higher (The Python License)"

#{ Check Types (enum, numerical ordering is significant)
CHECK_IS_GIF_FILE   = 0  #: Just check for a valid GIF header.
CHECK_IS_ANIMATED   = 1  #: Check whether the file has more than one frame.
CHECK_COUNT_FRAMES  = 2  #: Count the number of frames in the file.
CHECK_PARSE_PALETTE = 3  #: Parse the palette and resolve the background color.
CHECK_READ_COMMENTS = 4  #: Load comments (can sometimes be large) into the L{GifInfo} object.
CHECK_READ_ALL_TEXT = 5  #: Also load the contents of Plain Text extension blocks.

CHECK_ALL = CHECK_READ_ALL_TEXT #: alias to allow for future modifications

#{  Warning Codes (bitfield)
WARN_NONE = 0        #: No warnings
WARN_BAD_IMG = 1     #: Corruption (of the [sub]block size field(s)) or truncation detected in an image block
WARN_BAD_EXT = 2     #: Corruption (of the [sub]block size field(s)) or truncation detected in an extension block
WARN_BAD_SIZE = 4    #: An image block specifies dimensions exceeding the global canvas size
WARN_BAD_BGCOLOR = 8 #: The background color index specified is greater than the palette size
WARN_EOF  = 16       #: File is missing it's trailer. (Corrupt elsewhere, truncated, or breaking spec by using EOF as the terminator.)
WARN_TRUNC  = 32     #: File is definitively either truncated or corrupt. (An EOF was encountered part-way through a structure.)
WARN_LOOP_POS = 64   #: Netscape Application Extension block (animation-control) was present but not first in the file.
#}

import struct

#{ Structures used by GifInfo
gifHeaderStruct = struct.Struct('<xxxxxxHHBBB')  #: File header
gifImageStruct = struct.Struct('<HHHHB')         #: Image block header
gifExtenStruct = struct.Struct('<BB')            #: Top-level extension block header
gifNetscapeStruct = struct.Struct('<BBH')        #: NETSCAPE Loop-control sub-block
gifColorTripleStruct = struct.Struct('<BBB')     #: RGB palette element
gifPlaintextStruct = struct.Struct('<BHHHHBBBB') #: Plain Text block header
#}

class BadHeaderException(Exception):
    """Raised when no valid GIF header is found"""

class GifInfo(object):
    """A class for loading and storing metadata from GIF files.

    Accepts paths and file-like objects.

    When using L{CHECK_ALL}, this can also be used to walk past a valid
    GIF file in an un-delimited byte stream in order to identify the point at
    which the following file starts. (It doesn't C{fh.seek(0)} or C{fh.close()} after
    use)
    """
    warnFlags = WARN_NONE  #: A bit field of C{WARN_*} flags set by L{__init__}
    checkLevel = CHECK_ALL #: Default C{CHECK_*} level used by L{__init__}

    #{ Pre-defined "unset" values for GIF Metadata
    path = None        #: The path to the file, if one was passed to L{__init__}
    version = None     #: C{87a} or C{89a}
    width = None
    height = None
    loopCount = None
    pixelAspect = None
    paletteSize = None #: Always calculated if a global palette is present
    palette = None     #: The palette as a list of integer RGB tuples. Requires L{CHECK_PARSE_PALETTE}.
    bgColor = None     #: Global background color as an RGB tuple. Requires L{CHECK_PARSE_PALETTE}.
    comments = None    #: Text in Comment (0xFE) extension blocks as a list of strings. Requires L{CHECK_READ_COMMENTS}
    otherText = None   #: Text in "Plain Text" (0x01) extension blocks as a list of strings. Requires L{CHECK_READ_ALL_TEXT}
    frameCount = 0
    #}

    def __init__(self, fh, checkLevel=checkLevel):
        """
        @param fh: A path or file-like object for a GIF file.
        @param checkLevel: A C{CHECK_*} constant.

        @raises BadHeaderException: The given file lacks a valid GIF header.
        @raises IOError: The underlying C{open()} system call failed.
        """
        self.checkLevel = checkLevel
        if isinstance(fh, basestring):
            self.path = fh
            fh = open(fh, 'rb')

        header = fh.read(gifHeaderStruct.size)
        if len(header) < gifHeaderStruct.size:
            raise BadHeaderException("File is too small to be a GIF")

        self.version = header[3:6]
        if header[0:3] != 'GIF' or self.version not in ['87a', '89a']:
            raise BadHeaderException("File does not have a recognizable GIF header")
        elif self.checkLevel <= CHECK_IS_GIF_FILE:
            return

        self.width, self.height, GCTF_Byte, bgColor, self.pixelAspect = gifHeaderStruct.unpack(header)

        if self.pixelAspect:
            self.pixelAspect = (self.pixelAspect + 15) / 64.0

        rawPalette = self._getPalette(fh, GCTF_Byte)
        self.paletteSize = int(len(rawPalette) / 3)
        if self.checkLevel >= CHECK_PARSE_PALETTE:
            self.palette = []
            for pos in range(0, self.paletteSize):
                self.palette.append(gifColorTripleStruct.unpack_from(rawPalette, pos * 3))

        if self.paletteSize and bgColor > self.paletteSize:
            self.warnFlags = self.warnFlags | WARN_BAD_BGCOLOR
        elif self.palette:
            self.bgColor = self.palette[bgColor]

        # Iterate blocks
        self.firstBlock = True
        blocktype = self._read(fh, 1)
        while not blocktype == chr(0x3B) and not self.warnFlags & WARN_EOF:
            self._blockHandlers.get(blocktype, lambda x, y:'')(self, fh)
            if self.checkLevel <= CHECK_IS_ANIMATED and self.frameCount > 1:
                return

            self.firstBlock = False
            blocktype = self._read(fh, 1)

        del self.firstBlock

    def _handleImageBlock(self, fh):
        """"""
        self.frameCount += 1
        try:
            x, y, w, h, LCTF_Byte = gifImageStruct.unpack(self._read(fh, gifImageStruct.size))
        except:
            self.warnFlags = self.warnFlags | WARN_EOF | WARN_TRUNC
            return

        if x + w > self.width or y + h > self.height:
            self.warnFlags = self.warnFlags | WARN_BAD_SIZE

        self._getPalette(fh, LCTF_Byte) # Skip the local color table if present
        fh.read(1)                      # Skip the LZW minimum code size.

        # Skip content and test for the block terminator
        if not self._skipSubBlocks(fh): # For example, if it's a zero-length string like EOF would return.
            self.warnFlags = self.warnFlags | WARN_BAD_IMG

    def _handleGenericExtensionBlock(self, fh):
        """@todo: Rewrite this so extension block types have method handlers."""
        try:
            extType, blkSize = gifExtenStruct.unpack(self._read(fh, gifExtenStruct.size))
        except:
            self.warnFlags = self.warnFlags | WARN_EOF | WARN_TRUNC
            return
        startOffset = fh.tell()

        if extType == 0x01 and self.checkLevel >= CHECK_READ_ALL_TEXT: # Plain Text Block
            self._read(fh, gifPlaintextStruct.size)
            self.otherText = self.otherText or []
            blkSize = self._read(fh, 1)
            while blkSize and blkSize != '\x00':
                self.otherText.append(self._read(fh, ord(blkSize)))
                blkSize = self._read(fh, 1)
        elif extType == 0xFE and self.checkLevel >= CHECK_READ_COMMENTS: # Comment Block
            self.comments = self.comments or []
            blkSize = self._read(fh, 1)
            while blkSize and blkSize != '\x00':
                self.comments.append(self._read(fh, ord(blkSize)))
                blkSize = self._read(fh, 1)
        elif extType == 0xFF: # Application Block
            if blkSize == 0x0B and self._read(fh, blkSize) == "NETSCAPE2.0":
                try:
                    a, b, self.loopCount = gifNetscapeStruct.unpack(self._read(fh, gifNetscapeStruct.size))
                except:
                    self.warnFlags = self.warnFlags | WARN_EOF | WARN_TRUNC
                    return

                if a != 3 and b != 1:
                    self.warnFlags = self.warnFlags | WARN_BAD_EXT

                if not self.firstBlock:
                    self.warnFlags = self.warnFlags | WARN_LOOP_POS
        else:
            fh.seek( startOffset + blkSize ) # Skip the contents

        # Test for the block terminator
        if not self._skipSubBlocks(fh):
            self.warnFlags = self.warnFlags | WARN_BAD_EXT

    def _getPalette(self, handle, bitfield):
        """Using the size value from C{bitfield},
        load the palette at C{handle}'s current file pointer position."""
        if bitfield & int("10000000", 2):
            nBits = bitfield & int("00000111", 2)
            tableSize = 3 * 2**( nBits + 1 )
            return handle.read(tableSize)
        else:
            return ''

    def _read(self, handle, size):
        """Attempt to read the specified number of bytes. Set L{WARN_EOF} if
        fewer are received."""
        content = handle.read(size)
        if len(content) < size:
            self.warnFlags = self.warnFlags | WARN_EOF
        return content

    def _skipSubBlocks(self, handle):
        """Skip sub-blocks beginning at the current file pointer position
        using fseek."""
        offset = handle.tell()
        blkSize = handle.read(1)
        while blkSize and blkSize != '\x00':
            offset += ord(blkSize) + 1
            handle.seek(offset)
            blkSize = handle.read(1)
        return blkSize

    _blockHandlers = {
            chr(0x2C) : _handleImageBlock,
            chr(0x21) : _handleGenericExtensionBlock,
        }

def gif_is_animated(path):
    """A simple convenience function for testing whether a GIF is animated.
    @rtype: C{bool}
    """
    return GifInfo(file(path,'rb'), CHECK_IS_ANIMATED).frameCount > 1

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser(description=__doc__.split('\n\n')[0],
            version="%%prog v%s" % __version__, usage="%prog <path> ...")

    opts, args = parser.parse_args()

    if args:
        for fpath in args:
            try:
                info = GifInfo(fpath, CHECK_COUNT_FRAMES)
                warnFlags = (
                        (info.warnFlags & WARN_BAD_IMG     and 'I' or ' ') +
                        (info.warnFlags & WARN_BAD_EXT     and 'X' or ' ') +
                        (info.warnFlags & WARN_BAD_SIZE    and 'C' or ' ') +
                        (info.warnFlags & WARN_BAD_BGCOLOR and 'B' or ' ') +
                        (info.warnFlags & WARN_EOF         and 'E' or ' ') +
                        (info.warnFlags & WARN_TRUNC       and 'T' or ' ') +
                        (info.warnFlags & WARN_LOOP_POS    and 'L' or ' ')
                    )
                print "[%s](%3s Frames): %s" % (warnFlags, info.frameCount, info.path)
            except BadHeaderException, err:
                print "%s: %s" % (str(err), fpath)
        print "\nWarning Flags:"
        print " I = Image Chunk Corruption/Truncation"
        print " X = Extension Chunk Corruption/Truncation"
        print " C = Image Chunk Dimensions Exceed Global Canvas"
        print " B = Bad Background Color (Index Exceeds Palette Size)"
        print " E = Unexpected EOF Encountered (Missing Image Terminator)"
        print " T = EOF Encountered Within A Block Header (Corrupt or Truncated File)"
        print " L = Loop-control block misplaced within the file"
        print
        print "Note: A nearly-threefold speed-up can be had by using CHECK_IS_ANIMATED rather than CHECK_COUNT_FRAMES"
