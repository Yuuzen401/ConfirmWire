# ConfirmWire
ConfirmWireはblenderのアドオンです。

機能は選択したメッシュオブジェクトのエッジをGPUを利用して可視化します。
可視化したエッジは色・透明度・太さを変更できます。

他には以下のことができます。

1. エッジを左右反転で表示するかを切り替える
2. モディファイアによる変形後・変形前での可視を切り替える
3. 前後関係で隠れた線を可視・非可視を切り替える
4. 選択したオブジェクトまたエッジをアノテートに追加する

##### 1. エッジを左右反転で表示するかを切り替える
「左右反転」はシンメトリ構造を持ったオブジェクトの確認に使用することを想定しています。
ミラー適用後に片方を修正した場合に、片方との違いを確認することができます。

##### 2. モディファイアによる変形後・変形前での可視を切り替える
サブディビジョンサーフェイスやミラーによる評価が行われた状態での確認を想定しています。

##### 3. 前後関係で隠れた線を可視・非可視を切り替える
全てのエッジを可視化した場合に、後ろに隠れた線も見えてしまうため切り替えのスイッチを用意しています。
前後判定には法線の向きを利用しているので、表と裏が逆転した面を確認するのにも役立ちます。

##### 4. 選択したオブジェクトまたエッジをアノテートに追加する
選択したオブジェクトまたエッジをアノテートに追加します。（複数追加可）

#### 非推奨
想定は上記の通りですが、GPUによる描画は負荷があるため頂点数が非常に多いオブジェクトに使用するのは推奨できません。

#### 動作
versionは3.4でのみ確認を行っています。
