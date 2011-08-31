#!/usr/bin/env python
# coding: utf-8
# =============================================================================
# Rock Band Drums Test
#   Plays sound samples for each of the Rock Band PS3 drum pads and foot pedal
#   using the pygame SDL wrapper
# Copyright (C) 2009 Zach "theY4Kman" Kanzler
# =============================================================================
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License, version 3.0, as published by the
# Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import time
import cPickle
from ConfigParser import ConfigParser
from threading import Timer

import pygtk
pygtk.require("2.0")
import gtk
import gtk.glade

import pygame
from pygame.locals import *

__version__ = "1.0"

class RockBandDrumsException(Exception):
    pass

class RockBandDrums:
    """
    Allows the PS3's (and potentially other consoles') drum set to be linked to
    sound samples, which will be played when each pad is hit. Also provides a
    saving and replaying mechanism.
    """
    
    CONFIG_FILE = "rock_band_drums.cfg"
    PAD_NAMES = ["blue", "green", "red", "yellow", "pedal"]
    SAVE_FOLDER = "records"
    
    def __init__(self, joystick_id=0):
        # pygame Init
        pygame.init()
        
        self.joy = pygame.joystick.Joystick(joystick_id)
        self.joy.init()
        
        # General Initialization
        self.loop_quit = False
        
        self.sounds = None
        self.soundnames = None
        self.soundnums = None
        
        self.get_config()
        
        # PyGTK Init
        self.gui_tree = gtk.glade.XML("glade/rockbanddrums.glade")
        
        self.window = self.gui_tree.get_widget("mainwindow")
        self.window.connect("destroy", self.gui_cb_main_quit)
        
        handlers = {
            "on_about_activate": self.gui_cb_show_about_dialog,
        }
        self.gui_tree.signal_autoconnect(handlers)
        
        self.about_dialog = self.gui_tree.get_widget("aboutdialog")
        
        self.setup_images()
    
    def gui_cb_main_quit(self, event):
        self.save_config()
        self.loop_quit = True
    
    def gui_cb_show_about_dialog(self, event):
        about = gtk.AboutDialog()
        about.connect("response", lambda d,r: r == gtk.RESPONSE_CLOSE and d.destroy())
        
        # Close button
        about.get_children()[0].get_children()[1].get_children()[-1].connect("clicked",
            lambda e: about.destroy())
        
        about.set_name("Rock Band Drums")
        about.set_version(__version__)
        about.set_copyright(u"Copyright © 2009 Zach \"theY4Kman\" Kanzler")
        about.set_license("""\
        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <http://www.gnu.org/licenses/>.\
        """)
        about.set_website("http://y4kstudios.com")
        
        about.show()
    
    def setup_images(self):
        """Readies the drum set images"""
        self.gui_drum_image = self.gui_tree.get_widget("drums_image")
        self.gui_drum_image.set_from_file("data/drums.jpg")
        
        self.gui_pads = []
        for pad in self.PAD_NAMES:
            gui_pad = self.gui_tree.get_widget(pad + "_press")
            gui_pad.set_from_file("data/%s_press.png" % pad)
            gui_pad.hide()
            self.gui_pads.append(gui_pad)
    
    def replay(self, trackfile):
        """Replays a saved beat."""
        trackopen = open(trackfile, "rb")
        
        # We use pickle to make saving and loading easy.
        record = cPickle.load(trackopen)
        trackopen.close()
        
        soundnames = record[0]
        track = record[1]
        
        length = len(track)
        if length == 0:
            raise RockBandDrumsException("No sounds contained in this record file")
            return
        
        print "%d sounds in this record file." % length
        
        slen = len(soundnames)
        channels = [pygame.mixer.Channel(x) for x in xrange(slen)]
        sounds = [[] for x in xrange(slen)]
        
        for tr in track:
            diff = tr[1] - len(sounds[tr[0]]) + 1
            if diff > 0:
                sounds[tr[0]] += [None] * diff
            if sounds[tr[0]][tr[1]] is None:
                sounds[tr[0]][tr[1]] = pygame.mixer.Sound(soundnames[tr[0]] % tr[1])
        
        diff = time.time() - track[0][2]
        idx = 0
        while True:
            # Handle GUI
            gtk.main_iteration_do(False)
            
            cur = time.time() - diff
            if cur >= track[idx][2]:
                channels[track[idx][0]].play(sounds[track[idx][0]][track[idx][1]])
                idx += 1
                if idx >= length:
                    break

    def get_config(self):
        """Retrieves values from the configuration file to load sounds"""
        cfg = ConfigParser()
        cfg.read(self.CONFIG_FILE)
        
        self.soundnums = []
        self.soundnames = []
        
        for pad in self.PAD_NAMES:
            self.soundnames.append(cfg.get("samples", pad, True))
            self.soundnums.append(cfg.getint("sample_nums", pad))
        
        self.sounds = [pygame.mixer.Sound(self.soundnames[x] % self.soundnums[x]) \
             for x in xrange(len(self.soundnames))]
    
    def save_config(self):
        """Save the soundnums and soundnames to the config file"""
        cfg = ConfigParser()
        cfg.add_section("samples")
        cfg.add_section("sample_nums")
        
        for i,pad in enumerate(self.PAD_NAMES):
            cfg.set("samples", pad, self.soundnames[i])
            cfg.set("sample_nums", pad, self.soundnums[i])
        
        cfg_file = open(self.CONFIG_FILE, "w+")
        cfg.write(cfg_file)
        cfg_file.close()
    
    def play(self):
        """Just catches KeyboardInterrupt and saves the configuration"""
        try: self._play()
        except KeyboardInterrupt: pass
        
        self.save_config()

    def _play(self):
        """
        Play sounds when drum pads are hit, as well as other advanced features such
        as recording and dynamically changing the samples for each pad.
        """
        
        if self.sounds is None or self.soundnames is None or \
            self.soundnums is None:
            raise RockBandDrumsException("Sample sounds not loaded correctly")
        
        change_mode = False
        record_mode = False
        
        record = []
        record_time = 0
        
        # Each sample has its own channel
        channels = [pygame.mixer.Channel(x) for x in xrange(len(self.soundnames))]
        
        # Clear the events accumulated
        pygame.event.get()
        
        # Use a clock to prevent high CPU usage
        clock = pygame.time.Clock()
        
        while not self.loop_quit:
            clock.tick(40)
            
            # Handle GUI
            gtk.main_iteration_do(False)
            
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONUP:
                    if event.button <= 4:
                        self.gui_pads[event.button].hide()
                
                if event.type != pygame.JOYBUTTONDOWN:
                    continue
                
                if event.button == 12:
                    change_mode = not change_mode
                    if not change_mode:
                        self.save_config()
                    continue
                
                if event.button == 9:
                    record_mode = not record_mode
                    
                    if record_mode:
                        record = []
                        record_time = time.time()
                        print "Started recording..."
                    if not record_mode:
                        if not os.path.exists(self.SAVE_FOLDER):
                            os.mkdir(self.SAVE_FOLDER)
                        
                        savefile = time.strftime(self.SAVE_FOLDER + 
                            "/%m-%d-%Y_%H:%M:%S.record")
                        save = open(savefile, "w")
                        
                        pickler = cPickle.Pickler(save)
                        pickler.dump((self.soundnames, record))
                        save.close()
                        
                        print "Recorded for %d seconds. Saved in %s" % \
                            (time.time() - record_time, savefile)
                    
                    continue
                
                if event.button > 4:
                    print "Unrecognized button/pad pressed:", event.button
                    continue
                
                self.gui_pads[event.button].show()
                
                if not change_mode:
                    channels[event.button].play(self.sounds[event.button])
                    
                    if record_mode:
                        record.append((event.button, self.soundnums[event.button], time.time()))
                else:
                    self.soundnums[event.button] += 1
                    if not os.path.exists(self.soundnames[event.button] % self.soundnums[event.button]):
                        self.soundnums[event.button] = 1
                    
                    self.sounds[event.button] = pygame.mixer.Sound(self.soundnames[event.button] % \
                        self.soundnums[event.button])
                    channels[event.button].play(self.sounds[event.button])

if __name__ == "__main__":
    import cProfile
    drums = RockBandDrums()
    
    if len(sys.argv) > 1:
        drums.replay(sys.argv[1])
    else:
        cProfile.run("drums.play()")

