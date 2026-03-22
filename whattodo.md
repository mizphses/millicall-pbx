Asteriskか何かでIP-PBXを作る。

## Phase 1
端末のLANポートにNWハブを刺すので、自ら172.20のNWのルーターとなってPBXを立てるようにして。
電話番号の付与などを、WEB UIで管理できるのが必須。
言語はできる限りPythonで書いて欲しい。保守性高く、クリーンアーキテクチャで。

## Phase 2
自動応答botを作る。適当なLLM(API経由でいい)と会話したい。
https://docs.coefont.cloud/ にあるCoeFont APIを前提に設計して。
使っていい音声ID: cbe4e152-40a5-4c0d-91cd-2fc27d60e6bd

  accesskey = 'B62ORXnd9Xf6FUBiacoUkxbvC'
  access_secret = 'cHejBUkovRNI1GCIkCetdx2clA2WNUCXHDncpwDp'
（これはプロジェクト内であなたに共有するのは問題ないです）
