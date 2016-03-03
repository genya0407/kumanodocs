# -*- coding:utf-8 -*-

from django.db import models
from django.utils import html
from datetime import date, datetime, time, timedelta
from django.db.models import Q
import csv
# Create your models here.

class Meeting(models.Model):
    '''ブロック会議'''
    meeting_date = models.DateField("日付")
    
    def __str__(self):
        return self.meeting_date.strftime('%Y-%m-%d')
    
    @classmethod
    def normal_meeting_queryset(cls):
        if datetime.now().time() >= time(hour=21):
            return cls.objects.filter(meeting_date__gte=(date.today() + timedelta(days=3))).order_by('meeting_date')
        else :
            return cls.objects.filter(meeting_date__gte=(date.today() + timedelta(days=2))).order_by('meeting_date')

    @classmethod
    def exists_normal(cls):
        return cls.normal_meeting_queryset().exists()
    
    @classmethod
    def append_meeting_queryset(cls):
        if datetime.now().time() <= time(hour=12):
            return cls.objects.filter(meeting_date__exact=(date.today()))
        elif time(hour=12) < datetime.now().time() and datetime.now().time() <= time(hour=22):
            return cls.objects.filter(Q(meeting_date__exact=(date.today())) | Q(meeting_date__exact=(date.today() + timedelta(days=1))))
        elif time(hour=22) < datetime.now().time():
            return cls.objects.filter(meeting_date__exact=(date.today() + timedelta(days=1)))
        else :
            return cls.objects.none()
    
    @classmethod
    def exists_append(cls):
        return cls.append_meeting_queryset().exists()

    @classmethod 
    def posting_table_meeting_queryset(cls):
        return cls.normal_meeting_queryset() or cls.append_meeting_queryset()

    @classmethod
    def posting_note_meeting_queryset(cls):
        if datetime.now().time() >= time(hour=18):
            return cls.objects.filter(meeting_date__exact=(date.today()))
        elif datetime.now().time() <= time(hour=18):
            return cls.objects.filter(meeting_date__exact=(date.today() - timedelta(days=1)))
        else:
            return cls.objects.none()
    
    @classmethod
    def exists_meeting_for_posting_note(cls):
        return cls.posting_note_meeting_queryset().exists()
    
    @classmethod
    def rearrange_issues_meeting_queryset(cls):
        if datetime.now().time() < time(hour=12):
            return cls.objects.filter(meeting_date__gte=(date.today() + timedelta(days=1)))
        else :
            return cls.objects.filter(meeting_date__gte=(date.today() + timedelta(days=2)))

    @classmethod
    def download_note_meeting_queryset(cls):
        return cls.objects.filter(meeting_date__lte=(date.today()))
    
    def is_migrated_from_old_system(self):
        if self.meeting_date < date(year=2015,month=9,day=30):
            return True
        else:
            return False

    def has_issue(self):
        return Issue.objects.filter(meeting__exact=self).exists()

    class Meta:
        verbose_name_plural = "ブロック会議の日程"
        ordering = ('-meeting_date',)

class IssueType(models.Model):
    '''議案の種類'''
    name = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "議案の種類"

class Issue(models.Model):
    '''議案'''
    meeting         = models.ForeignKey(Meeting,verbose_name="日付")
    issue_types     = models.ManyToManyField(IssueType,verbose_name="議案の種類")
    title           = models.TextField(verbose_name="タイトル")
    author          = models.TextField(verbose_name="文責者")
    text            = models.TextField(verbose_name="本文")
    vote_content    = models.TextField(verbose_name="採決内容",blank=True)
    hashed_password = models.TextField(verbose_name="パスワード")
    issue_order     = models.IntegerField(verbose_name="議案の順番",default=(-1))
    created_at      = models.DateTimeField(auto_now_add=True, null=True)
    updated_at      = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return self.title

    def get_qualified_title(self):
        return "【" + (str(self.issue_order) if self.issue_order > 0 else "追加議案") + "】" + self.title + "【" + "・".join([t.name for t in self.issue_types.all()]) + "】" 

    def get_title_with_types(self):
        return self.title + "【" + "・".join([t.name for t in self.issue_types.all()]) + "】" 

    def is_votable(self):
        return IssueType.objects.get(name__exact="採決") in self.issue_types.all()

    def notes(self):
        return Note.objects.filter(issue__exact=self).order_by('block__name')

    def get_qualified_title_for_note(self):
        return "【0 - " + (str(self.issue_order) if self.issue_order > 0 else "追加議案") + "】" + self.title + "【" + "・".join([t.name for t in self.issue_types.all()]) + "】" 

    def tables(self):
        return Table.objects.filter(issue=self)#.order_by('table_order')

    def tag_eliminated_text(self):
        return html.strip_tags(self.text)

    def is_editable(self):
        return (self.meeting in list(Meeting.normal_meeting_queryset()))
        
    @classmethod
    def posting_table_issue_queryset(cls):
        return cls.objects.filter(meeting__in = Meeting.posting_table_meeting_queryset())
    
    class Meta:
        verbose_name_plural = "ブロック会議の議案"
        ordering = ('-meeting__meeting_date','issue_order')
    
class Block(models.Model):
    '''ブロック'''
    name = models.TextField()

    def __str__(self):
        return self.name

    @classmethod
    def all_blocks(cls):
        return cls.objects.all()
    
    @classmethod
    def blocks_posted_notes(cls):
        if Meeting.posting_note_meeting_queryset().exists():
            meeting = Meeting.posting_note_meeting_queryset().get()
            issue   = Issue.objects.filter(meeting__exact=meeting).first()
            if issue == None:
                return []
            else:
                notes = Note.objects.filter(issue__exact=issue)
                return [note.block for note in notes]
        else:
            return []

    @classmethod
    def exists_blocks_posted_notes(cls):
        if cls.blocks_posted_notes() == []:
            return False
        else:
            return True

class Note(models.Model):
    '''議事録'''
    issue           = models.ForeignKey(Issue,verbose_name="議案")
    block           = models.ForeignKey(Block,verbose_name="ブロック")
    text            = models.TextField(blank=True)
    hashed_password = models.TextField()

    class Meta(object):
        unique_together = ('issue','block')

    def __str__(self):
        return self.block.name + " " + self.issue.title
    
    class Meta:
        verbose_name_plural = "ブロック会議の議事録"

class Table(models.Model):
    '''表'''
    issue           = models.ForeignKey(Issue,verbose_name="議案")
    caption         = models.TextField(verbose_name="表のタイトル")
    csv_text        = models.TextField(verbose_name="表")
    table_order     = models.IntegerField(verbose_name="表の順番",default=(-1))

    def __str__(self):
        return self.caption + "(議案:" + self.issue.title + ")"

    def get_list(self):
        return csv.reader(self.csv_text.split('\n'),delimiter = '\t')

    class Meta:
        verbose_name_plural = "表"
